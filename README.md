# baidu-free-transfer

百度网盘文件转存工具（绕过免费用户每次只能转存500个文件的限制）

## 为什么会有这个工具

我们在使用百度网盘的时候经常要将别人分享的文件（夹）转存到自己网盘里。以前在PC端是没有限制的，现在对于免费用户会有每次500个文件的上限。这样对于分享的文件数较多的场景非常麻烦，因此想到开发一个小工具来实现这样的目的。

目前github上已经有一些相同功能的项目，如：[BaiduFilesTransfers_Pro](https://github.com/acheiii/BaiduFilesTransfers_Pro)。但实际使用之后发现这个项目的实现有些缺陷，而且代码也不太好改，索性重新实现一下。

## 使用方法

```bash
$ python3 -m pip install -r requirements.txt
$ python3 -m baidutransfer $url -C $cookie -p $pwd -r $root
```

- `$url` 是百度网盘的分享地址，如：`https://pan.baidu.com/s/1yQ7wutp3m1XtEhsigf_X6A`或`https://pan.baidu.com/share/init?surl=yQ7wutp3m1XtEhsigf_X6A`
- `$cookie` 是网页登录到百度网盘后开发者工具获取到的cookie
- `$pwd` 是分享提取码，如果没有提取码不需要传这个参数（如果分享的链接中有pwd参数，-p参数可以省略）
- `$root`是指定存储到网盘的目录，如果没有此参数，默认存储到网盘根目录

由于cookie可以多次使用，因此支持将cookie保存在yaml格式的配置文件中，格式如下：

```yaml
cookie: "XXX=12345;"
```

工具会默认读取当前目录下的`config.yaml`文件，如果不是该文件名，需要使用`-c /path/to/config.yaml`参数指定配置文件路径。使用配置文件指定cookie时，不再需要使用`-C`参数指定cookie了。