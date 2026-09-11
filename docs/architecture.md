# 架构概览

```text
plugins/pm-copilot -> requirements/
apps/manager-web -> services/local-server -> packages/core
```

插件从目标项目读取代码与可选本地页面，正式输出只写入统一需求库。管理页只访问同源服务；服务提供集中索引、受控资产读取和仅回环地址可用的写接口。`packages/core` 不依赖浏览器或文件系统。`requirements/` 不提交，不使用数据库、云同步或遥测。

服务默认监听 `0.0.0.0:57391` 供可信局域网阅读；写请求需要当前浏览器完成编辑口令解锁，解锁令牌持久保存在 Git 忽略的本机需求库中，公开接口不返回本机路径。
