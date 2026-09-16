# Custom OpenClash Rules

这是 Aethersailor 普通重度分流版的个人远程 YAML 覆写模块。生成配置保留业务组的手动选择、地区 `url-test` 自动选择，以及订阅中的全部具体节点。

## OpenClash 远程覆写地址

原方案（上游普通重度分流版）：

```text
https://cdn.jsdelivr.net/gh/sqzhang0814/Custom_OpenClash_Rules@refs/heads/main/overwrite/yaml/Custom_Clash_Full.conf
```

Apple 方案（在原方案基础上增加 Apple 专用规则）：

```text
https://cdn.jsdelivr.net/gh/sqzhang0814/Custom_OpenClash_Rules@refs/heads/main/overwrite/yaml/Custom_Clash_Full_Apple.conf
```

在 OpenClash 的远程覆写模块中选择其中一个地址，并将模块变量 `EN_KEY1` 填为机场订阅链接。原方案下载 `Custom_Clash_Full.yaml`；Apple 方案下载 `Custom_Clash_Full_Apple.yaml`。两个方案相互独立，原方案的行为保持不变。

Apple 方案额外包含 `Apple_Update`、`Apple_PKI`、`Apple_iCloud_CN` 和 `Apple_Dev_CN` 四个 MetaCubeX 规则提供者。系统更新与 PKI 默认进入 `🍎 苹果系统服务`（默认 `🎯 全球直连`，可切换地区组或具体节点），中国区 iCloud 与开发者服务默认进入仅含 `DIRECT` 的 `🍎 苹果服务CN`。原有通用 `GEOSITE,apple` 规则继续指向 `🍎 苹果服务`。

## 自动更新

GitHub Actions 每日检查一次上游 `Aethersailor/Custom_OpenClash_Rules` 的普通重度分流 YAML 与覆写模块，并从同一份上游提交生成原方案和 Apple 方案。发现变化后会：

1. 从上游重新生成两个 YAML 与两个覆写模块；
2. 在两个 YAML 的 `rules:` 最前面插入 `custom-rules.yaml` 中的个人规则；
3. 仅在 Apple 方案中加入 Apple 规则提供者、策略组和规则顺序；
4. 验证地区组仍为 `url-test`，业务选择组仍通过 `provider1` 提供具体节点；
5. 验证两个 YAML 可解析后再提交。

上游结构不再满足这些条件时，工作流会失败并保留上一版有效配置。可在仓库 **Actions** 页面手动运行 `Sync custom OpenClash YAML` 立即更新。

## 修改个人规则

只编辑 [custom-rules.yaml](custom-rules.yaml)，然后手动运行同步工作流。不要直接编辑生成的 YAML 或 `.conf`，下次同步会覆盖它们。
