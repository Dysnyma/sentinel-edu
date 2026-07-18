#!/usr/bin/env bash
# 合并所有 .py 代码为一个 txt 文件，方便 LLM 上下文一次性阅读
# 用法: bash merge_py.sh [输出文件名]

set -euo pipefail

OUTPUT="${1:-all_py_code.txt}"
OUTPUT_DIR="$(cd "$(dirname "$0")" && pwd)"
OUTPUT_PATH="$OUTPUT_DIR/$OUTPUT"
ROOT="$OUTPUT_DIR"

echo "🔄 正在合并 Python 代码到: $OUTPUT_PATH"

# 收集所有 .py 文件（排除 .git/.claude/venv/__pycache__ 等）
FILES=()
while IFS= read -r -d '' f; do
    FILES+=("$f")
done < <(find "$ROOT" -name "*.py" \
    -not -path "*/.git/*" \
    -not -path "*/.claude/*" \
    -not -path "*/__pycache__/*" \
    -not -path "*/venv/*" \
    -not -path "*/.venv/*" \
    -not -path "*/node_modules/*" \
    -print0 | sort -z)

TOTAL="${#FILES[@]}"
echo "📦 共找到 $TOTAL 个 .py 文件"

# 写入头部信息
{
    echo "========================================"
    echo " Sentinel Edu — 全部 Python 源码合并"
    echo " 生成时间: $(date '+%Y-%m-%d %H:%M:%S')"
    echo " 文件总数: $TOTAL"
    echo "========================================"
    echo
} > "$OUTPUT_PATH"

COUNT=0
for f in "${FILES[@]}"; do
    REL="${f#$ROOT/}"
    LINES=$(wc -l < "$f")
    echo "  [$((COUNT+1))/$TOTAL] $REL ($LINES 行)"

    {
        echo "========================================"
        echo " 文件: $REL"
        echo " 路径: $f"
        echo " 行数: $LINES"
        echo "========================================"
        echo
        cat "$f"
        echo
        echo
    } >> "$OUTPUT_PATH"

    COUNT=$((COUNT + 1))
done

TOTAL_LINES=$(wc -l < "$OUTPUT_PATH")
echo "✅ 完成！合并文件: $OUTPUT_PATH"
echo "   总行数: $TOTAL_LINES"
echo "   文件大小: $(du -h "$OUTPUT_PATH" | cut -f1)"
