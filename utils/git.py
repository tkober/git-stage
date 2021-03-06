import subprocess

from git import Repo, RemoteReference, Head


class File:

    def untracked_file(relative_path):
        return File(relative_path, False, False, False, '?')

    def from_diff(diff, staged):
        change_type = diff.change_type
        if staged:
            if 'A' == change_type:
                change_type = 'D'
            elif 'D' == change_type:
                change_type = 'A'

        return File(diff.a_path, True, staged, diff.renamed_file, change_type)

    def __init__(self, relative_path, tracked, staged, renamed, change_type):
        super().__init__()
        self.__relative_path = relative_path
        self.__tracked = tracked
        self.__staged = staged
        self.__renamed = renamed
        self.__change_type = change_type

    def get_relative_path(self):
        return self.__relative_path

    def is_tracked(self):
        return self.__tracked

    def is_staged(self):
        return self.__staged

    def is_renamed(self):
        return self.__renamed

    def get_change_type(self):
        return self.__change_type


class Repository:

    def __init__(self, directory):
        super().__init__()
        self.repo = Repo(directory)
        self.__directory = directory

    def getDirectory(self):
        return self.__directory

    def active_branch(self):
        return self.repo.active_branch

    def active_branch_name(self):
        return self.active_branch().name

    def getBranches(self, local=True, remotes=False):
        refs = []
        for ref in self.repo.refs:
            if isinstance(ref, RemoteReference):
                if remotes:
                    refs.append(ref)
            elif isinstance(ref, Head):
                if local:
                    refs.append(ref)

        return [ Branch(ref, self.repo) for ref in refs ]

    def remotes(self):
        return self.repo.remotes

    def fetch(self):
        for remote in self.repo.remotes:
            remote.fetch()

    def hasDetachedHead(self):
        return self.repo.head.is_detached

class Branch:

    def __init__(self, reference, repo):
        super().__init__()
        self.head = reference.remote_head if isinstance(reference, RemoteReference) else reference.name
        self.remote = reference.remote_name if isinstance(reference, RemoteReference) else None
        self.reference = reference
        self.commitsBehind = None
        self.commitsAhead = None
        self.upstream = reference.tracking_branch()

        if self.upstream:
            commitsBehind = repo.iter_commits('{}..{}'.format(self.head, self.upstream))
            self.commitsBehind = sum(1 for c in commitsBehind)

            commitsAhead = repo.iter_commits('{}..{}'.format(self.upstream, self.head))
            self.commitsAhead = sum(1 for c in commitsAhead)

        self.diff = ''
        if self.commitsAhead:
            self.diff += '↑·{}'.format(self.commitsAhead)

        if self.commitsBehind:
            self.diff += '↓·{}'.format(self.commitsBehind)

    def __repr__(self):
        diff = ', diff={}'.format(self.diff) if self.diff and len(self.diff) else ''
        return '<Branch head={}, remote={}, upstream={}{} >'.format(self.head, self.remote, self.upstream, diff)


class Stage(Repository):

    def __init__(self, directory):
        super().__init__(directory)

    def status(self):
        result = self.__staged_files() + self.__unstaged_files() + self.__untracked_files()
        result.sort(key= lambda file: file.get_relative_path())
        return result

    def __staged_files(self):
        return [File.from_diff(diff, True) for diff in self.repo.index.diff(self.repo.head.commit)]

    def __unstaged_files(self):
        return [File.from_diff(diff, False) for diff in self.repo.index.diff(None)]

    def __untracked_files(self):
        return [File.untracked_file(f) for f in self.repo.untracked_files]

    def stash_all(self):
        self.repo.git.stash()

    def pop_stash(self):
        self.repo.git.stash('pop')

    def ignore(self, untracked_file):
        gitignore_path = self.repo.working_tree_dir + '/.gitignore'
        gitignore_file = open(gitignore_path, 'a')

        try:
            gitignore_file.write(untracked_file.get_relative_path())
        finally:
            gitignore_file.close()

    def checkout(self, file):
        if file.is_staged():
            self.reset(file)

        self.repo.git.checkout(file.get_relative_path())

    def add(self, file):
        self.repo.git.add(file.get_relative_path())

    def add_all(self):
        self.repo.git.add('-A')

    def reset(self, file):
        subprocess.Popen('git reset HEAD -- ' + file.get_relative_path(), shell=True).wait()

    def reset_all(self):
        self.repo.git.reset('HEAD')

