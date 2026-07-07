<div align="center">

<img src="../assets/app_icon.png" width="120" alt="大家的应急铃" />

# 大家的应急铃

### 在外面不知所措时——告诉您该打什么电话、该去哪里

[한국어](../README.md) · [English](README_Eng.md) · **中文**

<br>

[![PlayMCP](https://img.shields.io/badge/PlayMCP-可用-FEE500?style=flat-square)](https://playmcp.kakaocloud.io)
[![AGENTIC PLAYER 10](https://img.shields.io/badge/카카오_2026-AGENTIC_PLAYER_10-000?style=flat-square&logo=kakaotalk&logoColor=FEE500)](https://playmcp.kakaocloud.io)

> 在 **KakaoTalk** 里用一句话查询韩国 **官方公共数据**：厕所、药店、急诊、安全铃、地铁寄存、免费 WiFi 等。  
> 适合 **居民、游客、残障人士及夜间感到不安的用户**。

</div>

---

## 这是什么？

在韩国外出时，常常会遇到：该打 **119 还是 1339**、**夜间药店**在哪、**最近的厕所**、**夜路安全铃** 等问题。

**大家的应急铃（modu-emergencybell）** 连接 KakaoTalk 智能体后，用 **中文或英文** 提问，即可获得基于 **韩国公共数据** 的附近设施与下一步建议。

> **仅提供信息指引**，不代打电话、不诊断、不代为报警。

---

## 什么时候用

| 场景 | 可以这样问 |
|------|------------|
| 🚽 **急需厕所** | 「明洞圣堂附近哪里有厕所？很急！」 |
| 💊 **夜间/周日药店** | 「江南站附近有药店吗？头疼」 |
| 🌡️ **孩子发烧** | 「半夜孩子在麻浦区发烧39度，儿科和药店在哪？」 |
| 📞 **打哪个电话** | 「闻到煤气味，在韩国该打什么电话？」 |
| 🌙 **夜路害怕** | 「海云台晚上走路安全吗？有安全铃吗？」 |
| ♿ **轮椅厕所** | 「明洞圣堂附近有轮椅厕所吗？」 |
| 🧳 **地铁寄存** | 「釜山西面站能寄存行李吗？」 |
| 📶 **免费 WiFi** | 「弘大附近有免费 WiFi 吗？」 |

**一次问多件事：**

> 「在益善洞附近，妈妈膝盖流血了，急诊和药店请告诉我。」

---

## 怎么用

### KakaoTalk · PlayMCP 用户

1. 在 PlayMCP 中连接 **大家的应急铃** MCP。
2. 像聊天一样发送 **地点 + 情况**（中文即可）。
3. 智能体会返回附近设施、急救电话与建议行动。

**小贴士**
- 只要说大概位置即可：「江南」「明洞」「梨泰院」。
- 回答中的 **韩文地址请保留**，方便给司机或店员看。
- 智能体可将结果 **翻译成中文**。

### 开发者

| | |
|---|---|
| Endpoint | `https://modu-emergencybell-mcp.playmcp-endpoint.kakaocloud.io/mcp` |
| 标识符 | `modu-emergencybell` |

技术文档 → [DEPLOY_KC.md](DEPLOY_KC.md) · [TOOL_EXAMPLES.md](TOOL_EXAMPLES.md)

---

## 复制即用

```
明洞圣堂附近哪里有轮椅厕所？很急！
```

```
闻到煤气味应该打119还是1544？
```

```
弘大附近有免费 WiFi 吗？
```

```
海云台晚上走路安全吗？有安全铃吗？
```

更多示例 → [GLOBAL_KAKAOTALK.md](GLOBAL_KAKAOTALK.md) · `python scripts/global_tool_tests.py`

---

## 为谁服务

- 🧑‍🤝‍🧑 **普通市民** — 厕所、药店、急诊信息  
- 🌏 **外国游客** — 可用 **中文、英文** 提问  
- ♿ **残障人士与照护者** — 轮椅厕所、母婴设施  
- 🌙 **夜间安全** — 安全铃、儿童庇护场所  
- 🎖️ **功勋人员** — 委托医院指引  

---

## 注意事项

- 生命受到威胁时，请 **立即拨打 119**。
- 夜间/节假日医院、药店信息按 **日期** 提供，凌晨是否营业请 **电话确认**。
- 本服务 **仅供参考**，不提供医疗诊断或代为报警。

---

## 更多

| 文档 | |
|------|------|
| [한국어 README](../README.md) | 韩语用户指南 |
| [English README](README_Eng.md) | 英语用户指南 |
| [GLOBAL_KAKAOTALK.md](GLOBAL_KAKAOTALK.md) | 多语言测试与详情 |

---

<div align="center">

**Kakao 2026 AGENTIC PLAYER 10 · 预选赛提交**

大家的应急铃 — 为在韩国的 **每一个人** 指引下一步

</div>
