# Descoberta de skills irmas / dados (regra de independencia): a skill funciona
# instalada sozinha (symlink) sem depender da arvore do repo ao lado. Localiza:
#   1) $INEMAREF_HOME/skill/<x>
#   2) skill irma instalada  ~/.claude/skills/inemaref-<x>
#   3) repo via realpath (resolve o symlink de volta pro repo)
import os


def _find(name):
    here = os.path.dirname(os.path.realpath(__file__))   # .../skill/<this>/scripts
    cands = []
    home = os.environ.get("INEMAREF_HOME")
    if home:
        cands.append(os.path.join(home, "skill", name))
    cands.append(os.path.expanduser("~/.claude/skills/inemaref-" + name))
    cands.append(os.path.normpath(os.path.join(here, "..", "..", name)))
    for c in cands:
        if os.path.isdir(c):
            return c
    return cands[-1]


def scripts(name):
    return os.path.join(_find(name), "scripts")


def templates(name):
    return os.path.join(_find(name), "templates")


def referencias():
    return _find("referencias")
