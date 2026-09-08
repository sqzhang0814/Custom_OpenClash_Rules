# Custom OpenClash Rules

这是 Aethersailor 普通重度分流版的个人远程 YAML 覆写模块。生成配置保留业务组的手动选择、地区 `url-test` 自动选择，以及订阅中的全部具体节点。

## OpenClash 远程覆写地址

```text
https://cdn.jsdelivr.net/gh/sqzhang0814/Custom_OpenClash_Rules@refs/heads/main/overwrite/yaml/Custom_Clash_Full.conf
```

在 OpenClash 的远程覆写模块中添加这个地址，并将模块变量 `EN_KEY1` 填为机场订阅链接。模块会下载仓库中的 `Custom_Clash_Full.yaml`，无需再在 OpenClash 页面逐条添加个人规则。

## 自动更新

GitHub Actions 每日检查一次上游 `Aethersailor/Custom_OpenClash_Rules` 的普通重度分流 YAML 与覆写模块。发现变化后会：

1. 从上游重新生成 YAML 与覆写模块；
2. 在 `rules:` 最前面插入 `custom-rules.yaml` 中的个人规则；
3. 验证地区组仍为 `url-test`，业务选择组仍通过 `provider1` 提供具体节点；
4. 验证 YAML 可解析后再提交。

上游结构不再满足这些条件时，工作流会失败并保留上一版有效配置。可在仓库 **Actions** 页面手动运行 `Sync custom OpenClash YAML` 立即更新。

## 修改个人规则

只编辑 [custom-rules.yaml](custom-rules.yaml)，然后手动运行同步工作流。不要直接编辑生成的 YAML 或 `.conf`，下次同步会覆盖它们。
