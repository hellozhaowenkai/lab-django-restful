# lab-django-restful

## 介绍

Django RESTful 基础包，作为相关项目的 Git 子模块共享。

## 父模块开发

### 克隆

```bash
git clone --recursive
```

### 拉取

```bash
git pull --recurse-submodules=on-demand
```

### 推送

```bash
git push --recurse-submodules=on-demand
```

## 子模块开发

### 添加

```bash
git submodule add -b master git@gitee.com:dyai/lab-django-restful.git ./my_site/restful
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
git submodule update --init --recursive --remote
```

### 删除

```bash
git rm -rf --cached ./my_site/restful/
vim .gitmodules
vim .git/config
rm -rf .git/module/my_site/restful/
```
