#!/usr/bin/env python
# coding: utf-8
import datetime
import re
import signal
import sys
import time
import traceback
from os.path import abspath, exists, join

import click
import sh
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
from watchdog.observers.polling import PollingObserver


RE_GIT_FILE = re.compile(r'^(?:.*/\.git|\.git)(?:/.*)?$')


class Watcher(FileSystemEventHandler):

    def __init__(self, path, dest, duration=300, timeout=10*1000, use_polling_observer=False):
        super(Watcher, self).__init__()
        self.path = path
        self.dest = dest
        self.duration = float(duration) / 1000
        self.timeout = float(timeout) / 1000
        self.use_polling_observer = use_polling_observer
        self.gitignore = join(self.path, '.gitignore')
        signal.signal(signal.SIGINT, self._handle_sigint)
        self.events = []

    def _handle_sigint(self, signum, frame):
        sys.exit('Exiting...')

    def on_any_event(self, event):
        if RE_GIT_FILE.match(event.src_path):
            return
        what = 'directory' if event.is_directory else 'file'
        now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        msg = '%s %s %s: %s' % (now, event.event_type, what, event.src_path)
        self.events.append(msg)

    def _rsync(self):
        args = ['-avzpur', '--delete', '--force', '--exclude', '.git']
        if exists(self.gitignore):
            args.extend(['--exclude-from', self.gitignore])
        args.extend([self.path, self.dest])
        return sh.rsync(args, _timeout=self.timeout)

    def _retry(self, count):
        """
        ARGS:
            count: 已重试次数，重试越多则间隔时间越长
        """
        count = min(10, count)
        click.echo('retry...')
        time.sleep(self.duration*count)

    def rsync(self):
        count = 0
        while True:
            try:
                return self._rsync()
            except sh.TimeoutException:
                self._retry(count)
            except:
                traceback.print_exc()
                self._retry(count)
            count += 1

    def polling(self):
        if not self.events:
            return
        msg = self.events.pop()
        if self.events:
            msg = '{} and ...{} events'.format(msg, len(self.events))
            self.events[:] = []
        click.echo(msg.center(79, '-'))
        click.echo(self.rsync())

    def start(self):
        self.events.append('watching %s' % abspath(self.path))
        if self.use_polling_observer:
            observer = PollingObserver()
        else:
            observer = Observer()
        observer.schedule(self, self.path, recursive=True)
        observer.start()
        try:
            while True:
                self.polling()
                time.sleep(self.duration)
        except KeyboardInterrupt:
            observer.stop()
        observer.join()


@click.command()
@click.argument('path', required=True)
@click.argument('dest', required=True)
@click.option('-d', '--duration', default=300, help='watch duration(ms).')
@click.option('-t', '--timeout', default=10*1000, help='rsync timeout(ms).')
@click.option('--polling', is_flag=True, help='use polling observer.')
def main(path, dest, duration, timeout, polling):
    """
    Watch PATH and rsync to DEST

    Example: watch-rsync ./repo host:~/projects

    Note: A trailing slash on the PATH changes this behavior to avoid
          creating an additional directory level at the DEST.

    See also: https://linux.die.net/man/1/rsync
    """
    watcher = Watcher(path, dest, duration=duration, timeout=timeout, use_polling_observer=polling)
    watcher.start()


if __name__ == '__main__':
    main()
