---
name: mysql-query
description: Use when needing to query MySQL databases directly, when MySQL MCP server is unavailable or not loading, or when needing to explore database schemas and run SQL queries outside of MCP
---

# MySQL Query

> ⚠️ **跨设备迁移**：本 skill 含硬编码服务器信息和数据库密码示例，换设备后需修改：
>
> | 硬编码/配置 | 位置 | 新设备应改为 |
> |------------|------|-------------|
> | `222.71.55.27` | "Password with special characters" 示例 | 新服务器 IP |
> | `zhugedata` | 示例代码 database 参数 | 新数据库名 |
> | `root` / 密码 | 示例代码 | 新数据库凭据 |
> | `C:\Users\admin\...` | 不适用（Node.js 无路径依赖） | — |
>
> 🔒 **安全提醒**：示例中包含真实生产凭据，此文件不要提交到公开仓库。

## Overview

When MySQL MCP servers fail to load, use Node.js `mysql2` to query databases directly. This avoids adding non-Node dependencies (like Python pymysql) and works in any Node.js project.

## When to Use

- MySQL MCP server not showing up in available tools
- Need to run ad-hoc queries or explore schema
- MCP connection failing due to network/init timeout
- Need a quick DB check without restarting Claude Code

**Don't use for:**
- Write operations (INSERT/UPDATE/DELETE) on production — confirm with the user first
- Projects where `mysql2` can't be installed
- One-off queries that the MCP server would handle fine

## Quick Reference

| Operation | Command |
|-----------|---------|
| Install driver | `npm install mysql2` |
| Query all tables | `SHOW TABLES` |
| Describe table | `DESCRIBE table_name` or `SHOW CREATE TABLE table_name` |
| Row count | `SELECT COUNT(*) FROM table_name` |
| Sample rows | `SELECT * FROM table_name LIMIT 10` |
| Filter by DB | `SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA='db_name'` |

## Implementation

### Basic connection and query

Use an inline Node.js script. Always close the connection when done.

```bash
node -e "
const mysql = require('mysql2/promise');
(async () => {
  try {
    const conn = await mysql.createConnection({
      host: '<HOST>',
      port: <PORT>,
      user: '<USER>',
      password: '<PASSWORD>',
      database: '<DATABASE>',
      connectTimeout: 15000
    });
    const [rows] = await conn.execute('<SQL_QUERY>');
    console.table(rows);
    await conn.end();
  } catch(e) {
    console.log('Error:', e.message);
  }
})();
"
```

### Password with special characters

When the password contains backtick, `$`, `!`, `#`, or `~`:

```bash
# Use single-quoted heredoc to prevent shell expansion
node << 'EOF'
const mysql = require('mysql2/promise');
(async () => {
  const conn = await mysql.createConnection({
    host: '222.71.55.27',
    port: 3306,
    user: 'root',
    password: 'H`7noBSX8,~Ip#V!!',
    database: 'zhugedata',
    connectTimeout: 15000
  });
  const [rows] = await conn.execute('SHOW TABLES');
  console.table(rows);
  await conn.end();
})();
EOF
```

The `<< 'EOF'` (quoted) prevents ALL shell expansion, so special characters pass through literally.

### Parameterized queries

Use `?` placeholders — prevents SQL injection and handles special characters:

```bash
node -e "
const mysql = require('mysql2/promise');
(async () => {
  const conn = await mysql.createConnection({
    host: '<HOST>', port: <PORT>, user: '<USER>', password: '<PASSWORD>',
    database: '<DATABASE>', connectTimeout: 15000
  });
  const [rows] = await conn.execute(
    'SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA = ? AND TABLE_NAME LIKE ?',
    ['<db_name>', '%pattern%']
  );
  console.table(rows);
  await conn.end();
})();
"
```

### File-based script (.mjs)

For longer queries, write a temp file with `import` syntax. Same connection pattern applies.

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Password with `$` or backtick crashes in `node -e` | Use `node << 'EOF'` heredoc, not `node -e` |
| Installing pymysql (adds Python dependency) | Use `mysql2` — Node.js native, no extra language needed |
| Forgetting `connectTimeout` — hangs forever | Always set `connectTimeout: 15000` |
| Not calling `conn.end()` — process hangs | Always `await conn.end()` in try/catch/finally |
| Using shell variables for password | Pass literal password in heredoc to avoid shell interpolation |
| Running queries on wrong database | Always verify database name in `SHOW DATABASES` first |

## Red Flags

- Installing a new language's MySQL driver (pymysql, pg) when `mysql2` already works
- Connecting without `connectTimeout`
- Running INSERT/UPDATE/DELETE without user confirmation
- Leaving connections open (no `conn.end()`)
