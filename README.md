# lab-django-restful

## 介绍

Django RESTful 基础包，作为相关项目的 Git 子模块共享。

## 子模块开发

### 添加

```bash
cd lab-django-demo
git rm -rf ./my_site/restful
git submodule add git@gitee.com:dyai/lab-django-restful.git ./my_site/restful
```

### 修改

```bash
cd ./my_site/restful
git add --all
git commit
git push
```

### 初始化 & 更新

```bash
git submodule update --init --recursive
```

