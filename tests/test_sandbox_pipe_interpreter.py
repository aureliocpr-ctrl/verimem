"""Hunt finding [00]/[04]: pipe-smuggling of interpreters past the legacy denylist.

`echo X | python -c "..."` / `| node evil.js` matched the echo/cat allowlist while
the post-pipe denylist listed shells (bash/sh/pwsh) but OMITTED python/node/perl/
ruby/tee/xargs -> a NON-allowlisted interpreter could be reached via a pipe.

Defense-in-depth: the denylist now blocks any interpreter/util after a pipe/
semicolon/amp. (The deeper product decision "should the sandbox_exec MCP surface
expose `python -c` at all" is flagged separately; here we close the smuggle hole
without breaking the legacy read-only allowlist.)
"""
from verimem.sandbox import SandboxedShell


def test_pipe_into_interpreter_is_denied():
    sh = SandboxedShell()
    cmds = [
        'echo IGNORED | python -c "import os"',
        'echo x | python3 -c "1"',
        'echo x | node evil.js',
        'echo x | perl -e "print 1"',
        'cat f.txt | ruby -e "1"',
        'echo x | tee /tmp/out',
        'echo x | xargs rm',
    ]
    for cmd in cmds:
        r = sh.validate(cmd, cwd=".")
        assert not r.allowed, f"pipe-smuggle NOT denied: {cmd!r} -> {r.matched_rule}"


def test_plain_readonly_still_allowed():
    sh = SandboxedShell()
    for cmd in ["ls -la", "cat README.md", "git log --oneline -5", "echo hello world"]:
        r = sh.validate(cmd, cwd=".")
        assert r.allowed, f"legit read-only wrongly denied: {cmd!r} -> {r.matched_rule}"
