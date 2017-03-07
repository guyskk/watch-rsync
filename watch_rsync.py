#!/usr/bin/env python
# coding: utf-8
import datetime
import re
import time
import traceback
from os.path import abspath, exists, join

import click
import sh
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

RE_GIT_FILE = re.compile(r'^(?:.*/\.git|\.git)(?:/.*)?$')


class Watcher(FileSystemEventHandler):

    def __init__(self, path, dest, duration=300):
        super(Watcher, self).__init__()
        self.path = path
        self.dest = dest
        self.duration = duration
        self.gitignore = join(self.path, '.gitignore')

    def on_any_event(self, event):
        if RE_GIT_FILE.match(event.src_path):
            return
        what = 'directory' if event.is_directory else 'file'
        now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        msg = '%s %s %s: %s' % (now, event.event_type, what, event.src_path)
        click.echo(msg.center(79, '-'))
        click.echo(self.rsync())

    def rsync(self):
        args = ['-avz', '--delete', '--exclude', '.git']
        if exists(self.gitignore):
            args.extend(['--exclude-from', self.gitignore])
        args.extend([self.path, self.dest])
        try:
            return sh.rsync(args)
        except sh.ErrorReturnCode:
            traceback.print_exc()

    def start(self):
        observer = Observer()
        observer.schedule(self, self.path, recursive=True)
        observer.start()
        click.echo('watching %s' % abspath(self.path))
        click.echo(self.rsync())
        try:
            while True:
                time.sleep(float(self.duration)/1000)
        except KeyboardInterrupt:
            observer.stop()
        observer.join()


@click.command()
@click.argument('path', required=True)
@click.argument('dest', required=True)
@click.option('-d', '--duration', default=300, help='Watch duration(ms).')
def main(path, dest, duration):
    """
    Watch PATH and rsync to DEST

    Example: watch-rsync ./repo host:~/projects

    Note: A trailing slash on the PATH changes this behavior to avoid
          creating an additional directory level at the DEST.

    See also: https://linux.die.net/man/1/rsync
    """
    watcher = Watcher(path, dest, duration=duration)
    watcher.start()


if __name__ == '__main__':
    main()
