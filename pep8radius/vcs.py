import os
import re

from pep8radius.shell import (shell_out, shell_out_ignore_exitcode,
                              CalledProcessError)# with 2.6 compat

def using_git():
    try:
        git_log = shell_out(["git", "log"])
        return True
    except (CalledProcessError, OSError):  # pragma: no cover
        return False


def using_hg():
    try:
        hg_log = shell_out(["hg",   "log"])
        return True
    except (CalledProcessError, OSError):
        return False


def using_bzr():
    try:
        bzr_log = shell_out(["bzr", "log"])
        return True
    except (CalledProcessError, OSError):
        return False


class VersionControl(object):
    def __init__(self, root=None):
        if root is None:
            root = self.root_dir()
        self.root = root

    def _shell_out(self, *args, **kwargs):
        return shell_out(*args, cwd=self.root, **kwargs)

    @staticmethod
    def from_string(vc):
        try:
            return globals()[vc.title()]
        except KeyError:
            raise NotImplementedError("Unknown version control system.")

    @staticmethod
    def which():  # pragma: no cover
        """Try to see if they are using git or hg.
        return git, hg, bzr or raise NotImplementedError.

        """
        for (k, using_vc) in globals().items():
            if k.startswith('using_') and using_vc():
                return VersionControl.from_string(k[6:])

        # Not supported (yet)
        raise NotImplementedError("Unknown version control system, "
                                  "or you're not in the project directory.")

    # abstract methods
    @staticmethod
    def file_diff_cmd(r, file_name):  # pragma: no cover
        raise AbstractMethodError()

    @staticmethod
    def filenames_diff_cmd(r):  # pragma: no cover
        raise AbstractMethodError()

    @staticmethod
    def parse_diff_filenames(diff_files):  # pragma: no cover
        raise AbstractMethodError()

    @staticmethod
    def root_dir(cwd=None):  # pragma: no cover
        raise AbstractMethodError()

    def current_branch(self):  # pragma: no cover
        raise AbstractMethodError()

    @staticmethod
    def merge_base(rev1, rev2):  # pragma: no cover
        raise AbstractMethodError()

    def _branch_point(self, rev=None):
        current = self.current_branch()
        if rev is None:
            return current
        else:
            return self.merge_base(rev, current)

class Git(VersionControl):

    def current_branch(self):
        return self._shell_out(["git", "rev-parse", "HEAD"])

    @staticmethod
    def root_dir(cwd=None):
        root = shell_out(['git', 'rev-parse', '--show-toplevel'], cwd=cwd)
        return os.path.normpath(root)

    def merge_base(self, rev1, rev2):
        return self._shell_out(['git', 'merge-base', rev1, rev2])

    @staticmethod
    def file_diff_cmd(r, f):
        "Get diff for one file, f"
        return ['git', 'diff', r.rev, f]

    @staticmethod
    def filenames_diff_cmd(r):
        "Get the names of the py files in diff"
        return ['git', 'diff', r.rev, '--name-only']

    @staticmethod
    def parse_diff_filenames(diff_files):
        "Parse the output of filenames_diff_cmd"
        return diff_files.splitlines()


class Hg(VersionControl):

    def current_branch(self):
        return self._shell_out(["hg", "id"])[:12]  # this feels awkward

    @staticmethod
    def root_dir(cwd=None):
        return shell_out(['hg', 'root'], cwd=cwd)

    def merge_base(self, rev1, rev2):
        output = self._shell_out(['hg', 'debugancestor', rev1, rev2])
        return output.split(':')[1]

    @staticmethod
    def file_diff_cmd(r, f):
        "Get diff for one file, f"
        return ['hg', 'diff', '-r', r.rev, f]

    @staticmethod
    def filenames_diff_cmd(r):
        "Get the names of the py files in diff"
        return ["hg", "diff", "--stat", "-r", r.rev]

    @staticmethod
    def parse_diff_filenames(diff_files):
        "Parse the output of filenames_diff_cmd"
        # one issue is that occasionaly you get stdout from something else
        # specifically I found this in Coverage.py, luckily the format is
        # different (at least in this case)
        it = re.findall('(\n|^) ?(?P<file_name>.*\.py)\s+\|', diff_files)
        return [t[1] for t in it]


class Bzr(VersionControl):

    def current_branch(self):
        return self._shell_out(["bzr", "version-info",
                                "--custom", "--template={revision_id}"])

    @staticmethod
    def root_dir(cwd=None):
        return shell_out(['bzr', 'root'], cwd=cwd)

    def merge_base(self, rev1, rev2):
        # Note: find-merge-base just returns rev1 if rev2 is not found
        # we assume that rev2 is a legitamate revision.
        # the following raise a CalledProcessError if it's a bad revision
        shell_out(['bzr', 'log', '-c', rev1], cwd=self.root)

        output = shell_out_ignore_exitcode(['bzr', 'find-merge-base',
                                            rev1, rev2],
                                            cwd=self.root)
        # 'merge base is revision name@example.com-20140602232408-d3wspoer3m35'
        return output.rsplit(' ', 1)[1]

    @staticmethod
    def file_diff_cmd(r, f):
        "Get diff for one file, f"
        return ['bzr', 'diff', f, '-r', r.rev]

    @staticmethod
    def filenames_diff_cmd(r):
        "Get the names of the py files in diff"
        # TODO Can we do this better (without parsing the entire diff?)
        return ['bzr', 'status', '-S', '-r', r.rev]  # TODO '--from-root' ?

    @staticmethod
    def parse_diff_filenames(diff_files):
        "Parse the output of filenames_diff_cmd"
        # ?   .gitignore
        # M  0.txt
        files = []
        for line in diff_files.splitlines():
            line = line.strip()
            fn = re.findall('[^ ]+\s+(.*.py)', line)
            if fn and not line.startswith('?'):
                files.append(fn[0])
        return files
