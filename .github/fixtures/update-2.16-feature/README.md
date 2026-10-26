# Experimental feature migration fixture

Before/after contract fixture for `2.15.1 -> 2.16.0-experimental.1`: a PM-only
project with code review disabled receives the existing mechanically read-only
reviewer for mandatory `SPEC_REVIEW`. The product's atomic user model override,
manual instructions, owner text and foreign agent remain unchanged.

`check_update_fixtures.py` checks these preservation requirements and negative
controls. The files illustrate the documented target state; they do not execute
Codex migration instructions or prove a live project migration succeeded.
