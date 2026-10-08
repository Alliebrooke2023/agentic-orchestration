"""File tools, jailed to a root folder. Nothing is ever deleted or overwritten."""
import shutil
from pathlib import Path


class Jail:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def p(self, rel):
        path = (self.root / rel).resolve()
        if self.root != path and self.root not in path.parents:
            raise PermissionError(f"outside jail: {rel}")
        return path

    def _free(self, path):
        """Never overwrite: add _1, _2 ... if the target exists."""
        if not path.exists():
            return path
        i = 1
        while True:
            c = path.with_name(f"{path.stem}_{i}{path.suffix}")
            if not c.exists():
                return c
            i += 1

    def ls(self, rel="."):
        return sorted(x.name + ("/" if x.is_dir() else "") for x in self.p(rel).iterdir())

    def read(self, rel):
        return self.p(rel).read_text(encoding="utf-8", errors="replace")

    def write(self, rel, text):
        dst = self._free(self.p(rel))
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(text, encoding="utf-8")
        return str(dst.relative_to(self.root))

    def move(self, src, dst):
        s, d = self.p(src), self.p(dst)
        if not s.exists():
            raise FileNotFoundError(src)
        if d.is_dir():
            d = d / s.name
        d = self._free(d)
        d.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(s), str(d))
        return str(d.relative_to(self.root))

    def copy(self, src, dst):
        s, d = self.p(src), self.p(dst)
        if d.is_dir():
            d = d / s.name
        d = self._free(d)
        d.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(s, d)
        return str(d.relative_to(self.root))
