#!/bin/bash
# ==============================================
# Sentinel-Edu 一键代码体检脚本
# 工具：flake8 + bandit + pip-audit
# 输出：code_audit_report.md
# ==============================================

set -e

REPORT_FILE="code_audit_report.md"
SCAN_DIRS="core/ views/ app.py"

echo "=================================="
echo "  Sentinel-Edu 代码体检开始"
echo "=================================="

# ---------- 0. 检查并安装工具 ----------
echo ""
echo "[0/3] 检查依赖工具..."

check_and_install() {
    if ! python -m "$1" --version > /dev/null 2>&1; then
        echo "  → 安装 $1 ..."
        pip install "$1" -q
    else
        echo "  ✓ $1 已安装"
    fi
}

check_and_install flake8
check_and_install bandit
check_and_install pip-audit

# ---------- 1. 生成报告头部 ----------
echo ""
echo "[1/3] 生成报告..."

cat > "$REPORT_FILE" << 'EOF'
# Sentinel-Edu 代码体检报告

> 自动生成时间：__GENERATED_TIME__
> 扫描范围：core/、views/、app.py、全部依赖

---

EOF

# 写入生成时间
sed -i "s/__GENERATED_TIME__/$(date '+%Y-%m-%d %H:%M:%S')/g" "$REPORT_FILE"

# ---------- 2. flake8 语法与规范检查 ----------
echo ""
echo "[2/3] 运行 flake8 语法检查..."

{
    echo "## 一、语法与规范检查（flake8）"
    echo ""
    echo "### 扫描命令"
    echo '```bash'
    echo "flake8 $SCAN_DIRS --max-line-length=120 --ignore=E501,W503"
    echo '```'
    echo ""
    echo "### 问题清单"
    echo '```'
} >> "$REPORT_FILE"

# 运行 flake8，允许非零退出码（有问题就会返回非0）
flake8 $SCAN_DIRS --max-line-length=120 --ignore=E501,W503 >> "$REPORT_FILE" 2>&1 || true

# 统计问题数
FLAKE8_COUNT=$(flake8 $SCAN_DIRS --max-line-length=120 --ignore=E501,W503 2>/dev/null | wc -l)

{
    echo '```'
    echo ""
    echo "**问题总数：${FLAKE8_COUNT} 个**"
    echo ""
    if [ "$FLAKE8_COUNT" -eq 0 ]; then
        echo "> ✅ 未发现语法与规范问题"
    else
        echo "> ⚠️ 存在代码规范/潜在语法问题，建议逐条查看"
    fi
    echo ""
    echo "---"
    echo ""
} >> "$REPORT_FILE"

# ---------- 3. bandit 安全风险扫描 ----------
echo "[3/3] 运行 bandit 安全扫描..."

{
    echo "## 二、安全风险检查（bandit）"
    echo ""
    echo "### 扫描命令"
    echo '```bash'
    echo "bandit -r $SCAN_DIRS"
    echo '```'
    echo ""
    echo "### 问题清单"
    echo '```'
} >> "$REPORT_FILE"

bandit -r $SCAN_DIRS >> "$REPORT_FILE" 2>&1 || true

{
    echo '```'
    echo ""
    echo "---"
    echo ""
} >> "$REPORT_FILE"

# ---------- 4. pip-audit 依赖漏洞扫描 ----------
echo ""
echo "[4/4] 运行 pip-audit 依赖漏洞扫描..."

{
    echo "## 三、第三方依赖漏洞（pip-audit）"
    echo ""
    echo "### 扫描命令"
    echo '```bash'
    echo "pip-audit"
    echo '```'
    echo ""
    echo "### 漏洞清单"
    echo '```'
} >> "$REPORT_FILE"

pip-audit >> "$REPORT_FILE" 2>&1 || true

{
    echo '```'
    echo ""
    echo "---"
    echo ""
} >> "$REPORT_FILE"

# ---------- 5. 报告尾部 ----------
cat >> "$REPORT_FILE" << 'EOF'
## 四、说明

1. **flake8**：检查语法错误、未使用变量、导入冗余、代码风格等显性问题
2. **bandit**：检查安全漏洞，如明文密钥、命令注入、危险函数调用等
3. **pip-audit**：检查第三方依赖库的已知安全漏洞

### 修复建议优先级
- 🔴 **High / 高危**：立即修复
- 🟡 **Medium / 中危**：建议修复
- 🟢 **Low / 低危**：按需修复
- ⚪ 格式规范类：不影响运行，可统一整理时修复

EOF

# ---------- 完成提示 ----------
echo ""
echo "=================================="
echo "  ✓ 体检完成！"
echo "  报告已生成：$REPORT_FILE"
echo "  flake8 问题数：$FLAKE8_COUNT"
echo "=================================="
echo ""
echo "查看报告："
echo "  cat $REPORT_FILE"
echo "  或者直接用 VS Code 打开查看"
echo ""