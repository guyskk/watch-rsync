#!/usr/bin/env python
# coding: utf-8
import datetime
import time
from os.path import abspath

import click
import sh
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer


class Watcher(FileSystemEventHandler):

    def __init__(self, path, dest, duration=300):
        super(Watcher, self).__init__()
        self.path = path
        self.dest = dest
        self.duration = duration

    def on_any_event(self, event):
        what = 'directory' if event.is_directory else 'file'
        now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        msg = '%s %s %s: %s' % (now, event.event_type, what, event.src_path)
        click.echo(msg.center(79, '-'))
        click.echo(self.rsync())

    def rsync(self):
        # http://stackoverflow.com/questions/13713101/rsync-exclude-according-to-gitignore-hgignore-svnignore-like-filter-c
        return sh.rsync('-avz', '--delete', '--exclude', '.git',
                        '--filter', ':- .gitignore', self.path, self.dest)

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
