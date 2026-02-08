import asyncio
from dataclasses import dataclass
from pathlib import Path


@dataclass
class MergeResult:
    success: bool
    conflicts: list[str]
    commit_hash: str | None


async def _git(*args: str, cwd: Path) -> str:
    """Run a git command, return stdout. Raises on non-zero exit."""
    proc = await asyncio.create_subprocess_exec(
        "git",
        *args,
        cwd=cwd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {stderr.decode()}")
    return stdout.decode()


async def init_repo(graph_root: Path) -> None:
    """Initialize git repo if not already one."""
    graph_root.mkdir(parents=True, exist_ok=True)
    (graph_root / "nodes").mkdir(exist_ok=True)
    if not (graph_root / ".git").exists():
        await _git("init", cwd=graph_root)
        await _git("commit", "--allow-empty", "-m", "init", cwd=graph_root)


async def create_worktree(graph_root: Path, branch_name: str) -> Path:
    """Create a git worktree in /tmp. Returns worktree path."""
    worktree_path = Path(f"/tmp/{branch_name}")
    await _git("worktree", "add", "-b", branch_name, str(worktree_path), cwd=graph_root)
    (worktree_path / "nodes").mkdir(exist_ok=True)
    return worktree_path


async def remove_worktree(graph_root: Path, worktree_path: Path, branch_name: str) -> None:
    """Remove worktree and delete branch. Force-removes (worktrees are disposable)."""
    try:
        await _git("worktree", "remove", "--force", str(worktree_path), cwd=graph_root)
    except RuntimeError:
        pass
    try:
        await _git("branch", "-D", branch_name, cwd=graph_root)
    except RuntimeError:
        pass


async def commit(cwd: Path, message: str) -> str:
    """Stage nodes/ and commit. Returns commit hash."""
    await _git("add", "nodes/", cwd=cwd)
    await _git("commit", "-m", message, cwd=cwd)
    result = await _git("rev-parse", "HEAD", cwd=cwd)
    return result.strip()


async def merge_worktree(graph_root: Path, branch_name: str) -> MergeResult:
    """Merge branch into main. On conflict, aborts and returns conflict list."""
    proc = await asyncio.create_subprocess_exec(
        "git",
        "merge",
        branch_name,
        cwd=graph_root,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()

    if proc.returncode == 0:
        hash_out = await _git("rev-parse", "HEAD", cwd=graph_root)
        return MergeResult(success=True, conflicts=[], commit_hash=hash_out.strip())

    status = await _git("status", "--porcelain", cwd=graph_root)
    conflicts = [line[3:] for line in status.splitlines() if line.startswith("UU ")]
    await _git("merge", "--abort", cwd=graph_root)
    return MergeResult(success=False, conflicts=conflicts, commit_hash=None)


async def git_log(cwd: Path, since: str | None = None, limit: int = 20) -> list[dict]:
    """Recent commits. Returns [{hash, message, timestamp, files_changed}, ...]"""
    args = ["log", f"--max-count={limit}", "--format=%H|%s|%aI"]
    if since:
        args.append(f"--since={since}")
    try:
        raw = await _git(*args, cwd=cwd)
    except RuntimeError:
        return []

    entries = []
    for line in raw.strip().splitlines():
        if not line:
            continue
        parts = line.split("|", 2)
        if len(parts) < 3:
            continue
        hash_, message, timestamp = parts
        try:
            diff = await _git("diff-tree", "--no-commit-id", "--name-only", "-r", hash_, cwd=cwd)
            files = [f for f in diff.strip().splitlines() if f]
        except RuntimeError:
            files = []
        entries.append(
            {
                "hash": hash_,
                "message": message,
                "timestamp": timestamp,
                "files_changed": files,
            }
        )
    return entries


async def git_diff(cwd: Path, ref: str) -> str:
    """Show what changed in a specific commit."""
    return await _git("show", "--stat", ref, cwd=cwd)
