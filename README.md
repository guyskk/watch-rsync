# watch-rsync

一个用来同步代码到服务器的工具

## 安装

```
pip install watch-rsync
```

## 使用

```
Usage: watch-rsync [OPTIONS] PATH DEST

  Watch PATH and rsync to DEST

  Example: watch-rsync ./repo host:~/projects

  Note: A trailing slash on the source changes this behavior to avoid
  creating an additional directory level at the destination.

  See also: https://linux.die.net/man/1/rsync

Options:
  -d, --duration INTEGER  Watch duration(ms).
  --help                  Show this message and exit.
```

另外，会自动忽略 `.gitignore` 中的文件，服务器上生成的不会删除
