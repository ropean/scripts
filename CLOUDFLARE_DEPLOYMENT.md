# Cloudflare Pages 部署指南

本文档提供详细的 Cloudflare Pages 部署说明，作为 GitHub Pages 的备选方案。

## 为什么选择 Cloudflare Pages？

- ⚡ **更快的全球访问**：Cloudflare 的全球 CDN 网络
- 🔄 **无限带宽**：不限制流量
- 🌍 **更好的中国访问**：相比 GitHub Pages 更稳定
- 🚀 **更快的构建**：通常比 GitHub Actions 更快
- 💰 **免费额度充足**：每月 500 次构建，无限请求

## 方案一：通过 GitHub Actions 自动部署（推荐）

### 1. 获取 Cloudflare API Token

1. 登录 [Cloudflare Dashboard](https://dash.cloudflare.com/)
2. 进入 **My Profile** > **API Tokens**
3. 点击 **Create Token**
4. 使用 **Edit Cloudflare Workers** 模板，或创建自定义 Token：
   - Permissions:
     - Account > Cloudflare Pages > Edit
   - Account Resources:
     - Include > Your Account
5. 复制生成的 Token

### 2. 获取 Account ID

1. 在 Cloudflare Dashboard 中，点击任意域名
2. 在右侧可以看到 **Account ID**
3. 复制 Account ID

### 3. 配置 GitHub Secrets

在你的 GitHub 仓库中：

1. 进入 **Settings** > **Secrets and variables** > **Actions**
2. 添加以下 secrets：
   - `CLOUDFLARE_API_TOKEN`: 你的 API Token
   - `CLOUDFLARE_ACCOUNT_ID`: 你的 Account ID

### 4. 创建 Cloudflare Pages 项目

1. 登录 [Cloudflare Dashboard](https://dash.cloudflare.com/)
2. 进入 **Workers & Pages**
3. 点击 **Create application** > **Pages**
4. 选择 **Connect to Git**（或 **Direct Upload**）
5. 项目名称：`scripts-collection`（或修改 `.github/workflows/deploy-cloudflare.yml` 中的 `projectName`）
6. 如果选择 Direct Upload，跳过 Git 连接

### 5. 启用工作流

工作流文件已创建：`.github/workflows/deploy-cloudflare.yml`

要启用它：

1. 将 `deploy-cloudflare.yml` 中的 `projectName` 改为你的项目名称
2. 提交并推送到 `release` 分支
3. GitHub Actions 将自动构建并部署到 Cloudflare Pages

### 6. 配置自定义域名（可选）

1. 在 Cloudflare Pages 项目设置中
2. 进入 **Custom domains**
3. 添加你的域名
4. 按照提示配置 DNS

## 方案二：通过 Wrangler CLI 本地部署

### 1. 安装 Wrangler

```bash
npm install -g wrangler
# 或使用项目本地安装
npm install --save-dev wrangler
```

### 2. 登录 Cloudflare

```bash
wrangler login
```

### 3. 构建项目

```bash
npm run docs:build
```

### 4. 部署到 Cloudflare Pages

```bash
wrangler pages deploy docs/.vitepress/dist --project-name=scripts-collection
```

### 5. 设置自动部署脚本

在 `package.json` 中添加：

```json
{
  "scripts": {
    "deploy:cloudflare": "npm run docs:build && wrangler pages deploy docs/.vitepress/dist --project-name=scripts-collection"
  }
}
```

然后运行：

```bash
npm run deploy:cloudflare
```

## 方案三：直接连接 GitHub（最简单）

### 1. 创建 Pages 项目

1. 登录 [Cloudflare Dashboard](https://dash.cloudflare.com/)
2. 进入 **Workers & Pages**
3. 点击 **Create application** > **Pages** > **Connect to Git**
4. 选择你的 GitHub 仓库 `ropean/scripts`
5. 配置构建设置：

```
Framework preset: VitePress
Build command: npm run docs:build
Build output directory: docs/.vitepress/dist
Root directory: (leave empty or /)
Branch: release
```

6. 添加环境变量（如果需要）：

   - `NODE_VERSION`: `20`

7. 点击 **Save and Deploy**

### 2. 自动部署

每次推送到 `release` 分支时，Cloudflare 会自动构建和部署。

## 配置说明

### 修改 base URL

如果使用自定义域名，需要修改 `docs/.vitepress/config.mjs`：

```javascript
export default defineConfig({
  // GitHub Pages 使用：
  base: "/scripts/",

  // 自定义域名或 Cloudflare Pages 使用：
  base: "/",

  // ...其他配置
});
```

### 环境变量

如果需要根据部署平台使用不同配置：

```javascript
export default defineConfig({
  base: process.env.CF_PAGES ? "/" : "/scripts/",
  // ...
});
```

## 对比：GitHub Pages vs Cloudflare Pages

| 特性       | GitHub Pages   | Cloudflare Pages  |
| ---------- | -------------- | ----------------- |
| 构建速度   | 中等           | 快                |
| 全球访问   | 较慢（中国）   | 快（包括中国）    |
| 带宽限制   | 100GB/月       | 无限制            |
| 构建次数   | 无限           | 500 次/月（免费） |
| 自定义域名 | 支持           | 支持              |
| HTTPS      | 自动           | 自动              |
| 部署方式   | GitHub Actions | Git/CLI/Actions   |

## 推荐部署策略

### 策略一：双部署（最佳）

同时部署到 GitHub Pages 和 Cloudflare Pages：

1. 保留 `.github/workflows/deploy-pages.yml`（GitHub Pages）
2. 启用 `.github/workflows/deploy-cloudflare.yml`（Cloudflare Pages）
3. 一次推送，两处部署

优点：

- 双重备份
- 用户可选择最快的访问地址

### 策略二：仅 Cloudflare Pages

1. 禁用 `.github/workflows/deploy-pages.yml`
2. 仅使用 Cloudflare Pages

优点：

- 更快的全球访问
- 中国访问更稳定

### 策略三：混合策略

- 主站：Cloudflare Pages
- 备用：GitHub Pages

## 故障排查

### 构建失败

1. 检查 Node.js 版本是否为 20
2. 确认依赖安装成功
3. 本地测试构建：`npm run docs:build`

### 部署失败

1. 检查 API Token 权限
2. 确认 Account ID 正确
3. 查看 Cloudflare Dashboard 中的构建日志

### 页面显示空白

1. 检查 `base` 配置是否正确
2. 检查浏览器控制台的错误信息
3. 确认构建产物在正确的目录

## 更多资源

- [Cloudflare Pages 文档](https://developers.cloudflare.com/pages/)
- [VitePress 部署指南](https://vitepress.dev/guide/deploy)
- [Wrangler 文档](https://developers.cloudflare.com/workers/wrangler/)

## 获取帮助

如有问题，请：

1. 查看 [Cloudflare Community](https://community.cloudflare.com/)
2. 在本仓库提 Issue
3. 查看 Cloudflare Pages 的构建日志

---

**注意**：推送到 `release` 分支时会同时触发两个部署工作流。如果只想使用一个，可以删除或禁用另一个工作流文件。
