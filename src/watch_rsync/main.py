# coding: utf-8
import datetime
import re
import os
import sys
import time
import warnings
import subprocess
from os.path import abspath, join, dirname

from .__version__ import __version__


VENDOR_PATH = abspath(join(dirname(__file__), 'vendor'))
sys.path.insert(0, VENDOR_PATH)

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    import click
    from watchdog.observers import Observer
    from watchdog.observers.polling import PollingObserver
    from watchdog.events import FileSystemEventHandler


RE_GIT_FILE = re.compile(r"^(?:.*/\.git|\.git)(?:/.*)?$")


class RsyncException(Exception):
    """rsync failed"""


def which(program, paths=None):
    """ takes a program name or full path, plus an optional collection of search
    paths, and returns the full path of the requested executable.  if paths is
    specified, it is the entire list of search paths, and the PATH env is not
    used at all.  otherwise, PATH env is used to look for the program """

    def is_exe(fpath):
        return (
            os.path.exists(fpath)
            and os.access(fpath, os.X_OK)
            and os.path.isfile(os.path.realpath(fpath))
        )

    found_path = None
    fpath, fname = os.path.split(program)

    # if there's a path component, then we've specified a path to the program,
    # and we should just test if that program is executable.  if it is, return
    if fpath:
        program = os.path.abspath(os.path.expanduser(program))
        if is_exe(program):
            found_path = program

    # otherwise, we've just passed in the program name, and we need to search
    # the paths to find where it actually lives
    else:
        paths_to_search = []

        if isinstance(paths, (tuple, list)):
            paths_to_search.extend(paths)
        else:
            env_paths = os.environ.get("PATH", "").split(os.pathsep)
            env_paths = [x.strip('"') for x in env_paths]
            paths_to_search.extend(env_paths)

        for path in paths_to_search:
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                found_path = exe_file
                break

    return found_path


class Watcher(FileSystemEventHandler):
    def __init__(
        self,
        path,
        dest,
        duration=300,
        timeout=10 * 1000,
        use_polling_observer=False,
        rsync="rsync",
    ):
        super(Watcher, self).__init__()
        self.path = path
        self.dest = dest
        self.duration = float(duration) / 1000
        self.timeout = float(timeout) / 1000
        self.use_polling_observer = use_polling_observer
        self.gitignore = join(self.path, ".gitignore")
        self.events = []
        self.rsync_path = which(rsync)
        if not self.rsync_path:
            raise click.BadParameter("{} not exists or not executable".format(rsync))

    def on_any_event(self, event):
        if RE_GIT_FILE.match(event.src_path):
            return
        what = "directory" if event.is_directory else "file"
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        msg = "%s %s %s: %s" % (now, event.event_type, what, event.src_path)
        self.events.append(msg)

    def _rsync(self):
        args = [self.rsync_path, "-avzpur", "--delete", "--force", "--exclude", ".git"]
        if os.path.exists(self.gitignore):
            args.extend(["--exclude-from", self.gitignore])
        args.extend([self.path, self.dest])
        p = subprocess.Popen(args, stdout=sys.stdout, stderr=subprocess.STDOUT)
        return_code = None
        try:
            time_begin = time.time()
            while time.time() - time_begin <= self.timeout:
                return_code = p.poll()
                if return_code is not None:
                    break
                time.sleep(0.05)
        finally:
            if return_code is None:
                p.terminate()
        if return_code is None:
            return_code = p.wait()
            msg = "rsync timeout and terminated, return code %s" % return_code
            raise RsyncException(msg)
        if return_code != 0:
            msg = "rsync failed, return code %s" % return_code
            raise RsyncException(msg)
        return return_code

    def _retry(self, count):
        """
        ARGS:
            count: 已重试次数，重试越多则间隔时间越长
        """
        sleep_time = min(10, count) * self.duration
        click.echo("retry#{}...".format(count + 1))
        time.sleep(sleep_time)

    def rsync(self):
        count = 0
        while True:
            try:
                return self._rsync()
            except Exception as ex:
                click.echo(ex)
                self._retry(count)
            count += 1

    def polling(self):
        if not self.events:
            return
        msg = self.events.pop()
        if self.events:
            msg = "{} and ...{} events".format(msg, len(self.events))
            self.events[:] = []
        click.echo(msg.center(79, "-"))
        self.rsync()

    def start(self):
        self.events.append("watching %s" % abspath(self.path))
        if self.use_polling_observer:
            observer = PollingObserver()
        else:
            observer = Observer()
        try:
            observer.schedule(self, self.path, recursive=True)
            observer.start()
        except OSError as ex:
            click.echo(ex)
            return
        try:
            while True:
                self.polling()
                time.sleep(self.duration)
        finally:
            observer.stop()
        observer.join()


@click.command()
@click.argument("path", required=True)
@click.argument("dest", required=True)
@click.option("-d", "--duration", default=300, help="watch duration(ms).")
@click.option("-t", "--timeout", default=30 * 1000, help="rsync timeout(ms).")
@click.option("--polling", is_flag=True, help="use polling observer.")
@click.option("--rsync", default="rsync", help="rsync executable.")
@click.version_option(version=__version__)
def main(path, dest, duration, timeout, polling, rsync):
    """
    Watch PATH and rsync to DEST

    Example: watch-rsync ./repo host:~/projects

    Note: A trailing slash on the PATH changes this behavior to avoid
          creating an additional directory level at the DEST.

    See also: https://linux.die.net/man/1/rsync
    """
    watcher = Watcher(
        path,
        dest,
        duration=duration,
        timeout=timeout,
        use_polling_observer=polling,
        rsync=rsync,
    )
    watcher.start()
