import streamlit as st
import pandas as pd
import plotly.express as px
import time
import os
import shutil
import tempfile
import random
import uuid
import json
import re
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from core.config import init_config
from core.asr import extract_audio_from_video, transcribe_audio_api, transcribe_audio_local, download_bilibili_video
from core.text_correction import correct_text
from core.poison_generator import generate_poison
from core.dfa_scanner import DFAScanner
from core.llm_scanner import llm_scan
from core.database import init_db, save_result, get_all_results, update_llm_result
from core.utils import texts_to_jsonl, merge_jsonl, load_jsonl
# ---------- 配置持久化 ----------
import json
CONFIG_FILE = os.path.join('data', 'apiconfig.json')


def save_config_to_file():
    config = {
        'openai_api_key': st.session_state.get('openai_api_key', ''),
        'openai_base_url': st.session_state.get('openai_base_url', ''),
        'llm_model': st.session_state.get('llm_model', ''),
    }
    os.makedirs('data', exist_ok=True)
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False)


def load_config_from_file():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
            for key, value in config.items():
                if key not in st.session_state or not st.session_state[key]:
                    st.session_state[key] = value
        except:
            pass


# ---------- 页面配置 ----------
st.set_page_config(
    page_title="思政课堂安全分析原型",
    layout="wide",
    menu_items={
        'Get help': None,
        'Report a bug': None,
        'About': None
    }
)

# ---------- 初始化 ----------
init_config()
load_config_from_file()  # 自动读取保存的配置
init_db()
os.makedirs("data", exist_ok=True)
os.makedirs("downloads", exist_ok=True)

# ---------- 辅助函数 ----------


def highlight_toxic(text, toxic_spans):
    if not toxic_spans:
        return text
    escaped = [re.escape(span) for span in toxic_spans]
    pattern = re.compile('|'.join(escaped), re.IGNORECASE)
    return pattern.sub(
        lambda m: f'<mark style="background-color:#ff4d4d; color:white; padding:0 2px;">{m.group()}</mark>',
        text
    )


def check_api_connection(api_key, base_url, model):
    """测试大模型 API 连通性，返回 (success, message)"""
    if not api_key or not base_url or not model:
        return False, "请填写 API Key、Base URL 和模型名称。"
    try:
        import openai
        client = openai.OpenAI(api_key=api_key, base_url=base_url)
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "测试连接"}],
            max_tokens=5,
            timeout=10
        )
        return True, f"✅ 连接成功 (模型响应: {resp.choices[0].message.content})"
    except Exception as e:
        return False, f"❌ 连接失败: {str(e)}"


def run_concurrently(tasks, max_workers=3, progress_placeholder=None, progress_text=""):
    """
    并发执行任务列表。
    tasks: list of (func, args_tuple)  或  (func, kwargs_dict)
    返回结果列表（按输入顺序）。
    """
    results = [None] * len(tasks)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_idx = {}
        for idx, task in enumerate(tasks):
            func, args = task[0], task[1] if len(task) > 1 else ()
            if isinstance(args, dict):
                future = executor.submit(func, **args)
            else:
                future = executor.submit(func, *args)
            future_to_idx[future] = idx

        completed = 0
        total = len(tasks)
        for future in as_completed(future_to_idx):
            idx = future_to_idx[future]
            try:
                results[idx] = future.result()
            except Exception as e:
                results[idx] = e
            completed += 1
            if progress_placeholder is not None:
                progress_placeholder.progress(
                    completed / total, text=f"{progress_text} {completed}/{total}")
    return results


# ---------- 侧边栏 ----------
st.sidebar.header("⚙️ 全局配置")
st.sidebar.subheader("大模型 API")
api_key = st.sidebar.text_input(
    "API Key", type="password", value=st.session_state.openai_api_key)
base_url = st.sidebar.text_input(
    "API Base URL", value=st.session_state.openai_base_url)
llm_model = st.sidebar.text_input("LLM 模型", value=st.session_state.llm_model)
col_save, col_clear = st.sidebar.columns(2)
with col_save:
    if st.button("💾 保存配置"):
        save_config_to_file()
        st.success("配置已保存")
with col_clear:
    if st.button("🗑️ 清除保存"):
        try:
            os.remove(CONFIG_FILE)
            st.success("已清除")
        except:
            pass
# API 测试按钮
if st.sidebar.button("🔍 测试连接"):
    ok, msg = check_api_connection(api_key, base_url, llm_model)
    if ok:
        st.sidebar.success(msg)
    else:
        st.sidebar.error(msg)

st.sidebar.caption("若无 API Key，大模型功能不可用。")

# 语音识别设置
st.sidebar.subheader("语音识别 (ASR)")
use_local_whisper = st.sidebar.checkbox("使用本地 Whisper 模型（免费，离线）", value=True)
local_whisper_model = None
if use_local_whisper:
    local_whisper_model = st.sidebar.selectbox(
        "模型大小",
        ["tiny", "base", "small", "medium", "large"],
        index=2,   # small
        help="越大越准确，但更慢更占内存。推荐 small 或 medium。"
    )

# 工具状态
st.sidebar.subheader("系统工具状态")
ffmpeg_available = shutil.which(st.session_state.ffmpeg_path) is not None
bbdown_available = shutil.which(st.session_state.bbdown_path) is not None
st.sidebar.caption(
    f"{'✅' if ffmpeg_available else '❌'} FFmpeg: {'可用' if ffmpeg_available else '未找到'}")
st.sidebar.caption(
    f"{'✅' if bbdown_available else '❌'} BBDown: {'可用' if bbdown_available else '未找到'}")

with st.sidebar.expander("⚙️ 高级工具配置（可选）"):
    new_ffmpeg = st.text_input(
        "FFmpeg 自定义路径", value=st.session_state.ffmpeg_path)
    new_bbdown = st.text_input(
        "BBDown 自定义路径", value=st.session_state.bbdown_path)
    if new_ffmpeg != st.session_state.ffmpeg_path:
        st.session_state.ffmpeg_path = new_ffmpeg
    if new_bbdown != st.session_state.bbdown_path:
        st.session_state.bbdown_path = new_bbdown

# 并发设置
concurrency = st.sidebar.slider(
    "并发请求数（加速生成/检测）", 1, 6, 3, help="同时调用大模型的数量，提高速度但可能触发限流。")

# 更新 session_state
st.session_state.openai_api_key = api_key
st.session_state.openai_base_url = base_url
st.session_state.llm_model = llm_model

api_ready = bool(api_key) and bool(base_url) and bool(llm_model)

# ---------- 主界面 ----------
st.title("🛡️ 课堂思政元素安全性分析原型系统")
st.markdown("---")

tab1, tab2, tab3 = st.tabs(["📥 测试集构建", "🔍 安全检测", "📊 可视化分析"])

# ================= Tab1: 测试集构建 =================
with tab1:
    st.header("步骤1：获取原始文本")
    input_method = st.radio(
        "选择输入方式", ["📁 上传音视频文件", "🔗 B站视频链接", "✏️ 直接输入文本"], horizontal=True)
    raw_texts = []

    prompt_text = "这是一堂关于马克思主义基本原理、毛泽东思想、邓小平理论、唯物辩证法、社会主义核心价值观的大学思政课。"

    if input_method == "📁 上传音视频文件":
        uploaded_file = st.file_uploader(
            "上传音频或视频", type=["wav", "mp3", "m4a", "mp4", "flv", "mkv"])
        if uploaded_file:
            suffix = Path(uploaded_file.name).suffix
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(uploaded_file.read())
                tmp_path = tmp.name

            st.info("正在处理文件...")
            if suffix.lower() in ['.mp4', '.flv', '.mkv']:
                try:
                    audio_path = extract_audio_from_video(
                        tmp_path, st.session_state.ffmpeg_path)
                    st.success("音频提取成功")
                except Exception as e:
                    st.error(f"提取音频失败：{e}")
                    st.stop()
            else:
                audio_path = tmp_path

            if use_local_whisper:
                with st.spinner(f"本地 Whisper ({local_whisper_model}) 转写中..."):
                    transcript = transcribe_audio_local(
                        audio_path, model_name=local_whisper_model, initial_prompt=prompt_text)
                st.success("转写完成")
            else:
                if not api_ready:
                    st.error("未配置大模型 API 密钥，无法使用云端 ASR。请启用本地 Whisper。")
                    st.stop()
                with st.spinner("云端 Whisper 转写中..."):
                    transcript = transcribe_audio_api(
                        audio_path, api_key, base_url, prompt_text)
                st.success("转写完成")

            st.text_area("转写结果（可手动编辑）", transcript, height=200)
            raw_texts = [s.strip() for s in transcript.replace(
                '。', '\n').split('\n') if s.strip()]

            try:
                os.unlink(tmp_path)
                if 'audio_path' in locals() and audio_path != tmp_path:
                    os.unlink(audio_path)
            except:
                pass

    elif input_method == "🔗 B站视频链接":
        bili_url = st.text_input("B站视频地址")
        if bili_url and st.button("开始解析并下载"):
            if not shutil.which(st.session_state.bbdown_path):
                st.error("BBDown 不可用，请检查安装")
            else:
                with st.spinner("使用 BBDown 下载中..."):
                    try:
                        info = download_bilibili_video(
                            bili_url, st.session_state.bbdown_path)
                        if info['subtitle']:
                            sub_text = Path(info['subtitle']).read_text(
                                encoding='utf-8')
                            st.success("找到人工字幕，跳过语音转写")
                            st.text_area("字幕内容", sub_text, height=150)
                            raw_texts = [s.strip() for s in sub_text.replace(
                                '。', '\n').split('\n') if s.strip()]
                        else:
                            st.info("无字幕，提取音频进行 ASR...")
                            audio_path = extract_audio_from_video(
                                info['video'], st.session_state.ffmpeg_path)
                            if use_local_whisper:
                                with st.spinner(f"本地 Whisper ({local_whisper_model}) 转写中..."):
                                    transcript = transcribe_audio_local(
                                        audio_path, model_name=local_whisper_model, initial_prompt=prompt_text)
                                st.success("转写完成")
                            else:
                                if not api_ready:
                                    st.error(
                                        "未配置 API 密钥，无法使用云端 ASR。请启用本地 Whisper。")
                                    st.stop()
                                transcript = transcribe_audio_api(
                                    audio_path, api_key, base_url, prompt_text)
                                st.success("转写完成")
                            raw_texts = [s.strip() for s in transcript.replace(
                                '。', '\n').split('\n') if s.strip()]
                    except Exception as e:
                        st.error(f"处理失败：{e}")

    elif input_method == "✏️ 直接输入文本":
        manual_text = st.text_area("请输入课堂文本", height=200)
        if manual_text:
            raw_texts = [s.strip() for s in manual_text.replace(
                '。', '\n').split('\n') if s.strip()]

    if raw_texts:
        st.session_state['raw_texts'] = raw_texts
        st.info(f"已获取 {len(raw_texts)} 条文本片段")

    # --- 步骤2：文本纠错（可选） ---
    st.markdown("---")
    st.header("步骤2：文本纠错（可选）")
    if st.session_state.get('raw_texts'):
        if st.button("✨ 开始大模型纠错"):
            if not api_ready:
                st.error("缺少 API 配置")
            else:
                corrected = []
                progress_bar = st.progress(0)
                for i, text in enumerate(st.session_state.raw_texts):
                    try:
                        corr = correct_text(text, api_key, base_url, llm_model)
                        corrected.append(corr)
                    except Exception as e:
                        st.warning(f"第{i}条纠错失败，保留原句：{e}")
                        corrected.append(text)
                    progress_bar.progress(
                        (i+1)/len(st.session_state.raw_texts))
                st.session_state['corrected_texts'] = corrected
                st.success("纠错完成")
    else:
        st.caption("请先获取原始文本")

    final_texts = st.session_state.get(
        'corrected_texts', st.session_state.get('raw_texts', []))

    # --- 步骤3：生成无毒 JSONL ---
    st.markdown("---")
    st.header("步骤3：生成无毒文本集（JSONL）")
    if final_texts:
        if st.button("📝 生成无毒 JSONL"):
            texts_to_jsonl(final_texts, 'data/clean_corpus.jsonl')
            st.session_state['clean_jsonl'] = 'data/clean_corpus.jsonl'
            st.success(
                f"无毒文本已保存至 data/clean_corpus.jsonl，共 {len(final_texts)} 条")
    else:
        st.caption("等待文本就绪")

    # --- 步骤4：投毒生成 ---
    st.markdown("---")
    st.header("步骤4：投毒生成有毒文本（红队测试）")
    clean_path = st.session_state.get('clean_jsonl')
    if clean_path and os.path.exists(clean_path):
        poison_ratio = st.slider("投毒比例", 0.1, 1.0, 0.3, step=0.1)
        if st.button("🦠 开始投毒生成"):
            if not api_ready:
                st.error("缺少 API 配置")
            else:
                clean_data = load_jsonl(clean_path)
                total = len(clean_data)
                poison_count = max(1, int(total * poison_ratio))
                selected = random.sample(clean_data, poison_count)

                # 构建并发任务
                tasks = [(generate_poison, (rec['text'], api_key,
                          base_url, llm_model)) for rec in selected]
                progress_bar = st.progress(0)
                raw_results = run_concurrently(
                    tasks,
                    max_workers=concurrency,
                    progress_placeholder=progress_bar,
                    progress_text="投毒生成中"
                )

                # 处理结果
                poisoned_records = []
                for i, (rec, res) in enumerate(zip(selected, raw_results)):
                    if isinstance(res, Exception):
                        st.warning(f"第{i}条投毒失败")
                        with st.expander("查看错误"):
                            st.exception(res)
                        continue
                    # 补充 id 等字段
                    res['id'] = str(uuid.uuid4())[:8]
                    res.setdefault('original_text', rec['text'])
                    res.setdefault('attack_strategy', '未知')
                    poisoned_records.append(res)

                # 写入投毒文件
                poison_file = 'data/poisoned_corpus.jsonl'
                with open(poison_file, 'w', encoding='utf-8') as f:
                    for rec in poisoned_records:
                        out = {
                            "id": rec['id'],
                            "text": rec.get('text', ''),
                            "is_toxic": True,
                            "toxic_spans": rec.get('toxic_spans', []),
                            "attack_strategy": rec.get('attack_strategy', '')
                        }
                        f.write(json.dumps(out, ensure_ascii=False) + '\n')

                merge_jsonl(clean_path, poison_file,
                            'data/final_test_mixed.jsonl')
                st.session_state['final_test'] = 'data/final_test_mixed.jsonl'
                st.success(
                    f"投毒完成！共生成 {len(poisoned_records)} 条有毒文本，最终混合集：data/final_test_mixed.jsonl")

                # 展示有毒样本对比
                final_data = load_jsonl('data/final_test_mixed.jsonl')
                toxic_samples = [r for r in final_data if r.get('is_toxic')]
                if toxic_samples:
                    with st.expander(f"🔍 有毒样本对比（共 {len(toxic_samples)} 条）"):
                        for i, rec in enumerate(toxic_samples[:10]):
                            original = rec.get('original_text', '（无法获取原文）')
                            toxic_text = rec.get('text', '')
                            spans = rec.get('toxic_spans', [])
                            strategy = rec.get('attack_strategy', '未知')
                            st.markdown(f"**样本 {i+1}** | 策略：{strategy}")
                            col1, col2 = st.columns(2)
                            with col1:
                                st.caption("原文")
                                st.write(original)
                            with col2:
                                st.caption("有毒文本（毒点高亮）")
                                st.markdown(highlight_toxic(
                                    toxic_text, spans), unsafe_allow_html=True)
                            st.markdown("---")
    else:
        st.caption("请先生成无毒 JSONL")

# ------------------- Tab2: 安全检测 -------------------
# ------------------- Tab2: 安全检测 -------------------
with tab2:
    st.header("双重安全检测")
    test_file = st.selectbox("选择测试集文件",
                             options=[f.name for f in Path(
                                 "data").glob('*.jsonl')],
                             index=0 if st.session_state.get('final_test') else None)
    if not test_file:
        st.info("请先构建测试集")
        st.stop()

    test_file_path = os.path.join("data", test_file)
    all_data = load_jsonl(test_file_path)
    st.success(
        f"已加载 {len(all_data)} 条样本，其中 {sum(1 for r in all_data if r.get('is_toxic'))} 条有毒")

    # 初始化数据库（如果尚未）
    init_db()
    # 将所有样本的 true_label 写入数据库（如果还未写入）
    for rec in all_data:
        true_label = 1 if rec.get('is_toxic') else 0
        try:
            # -1 表示未检测
            save_result(rec['id'], true_label, -1, -1, [], 0, 0, [])
        except:
            pass

    # ----- 功能按钮区 -----
    st.subheader("批量检测")
    col_btn1, col_btn2, col_btn3 = st.columns(3)

    with col_btn1:
        if st.button("🔰 仅 DFA 扫描"):
            scanner = DFAScanner('sensitive_words.txt')
            progress = st.progress(0)
            for i, rec in enumerate(all_data):
                text = rec['text']
                dfa_hit, dfa_words = scanner.scan(text)
                true_label = 1 if rec.get('is_toxic') else 0
                save_result(rec['id'], true_label, int(
                    dfa_hit), -1, dfa_words, 0, 0, [])
                progress.progress((i+1)/len(all_data))
            st.success("DFA 扫描完成")

    with col_btn2:
        if st.button("🤖 仅 LLM 扫描", disabled=not api_ready):
            tasks = [(llm_scan, (rec['text'], api_key, base_url, llm_model))
                     for rec in all_data]
            progress_bar = st.progress(0)
            llm_results = run_concurrently(
                tasks,
                max_workers=concurrency,
                progress_placeholder=progress_bar,
                progress_text="LLM 扫描中"
            )
            for i, (rec, res) in enumerate(zip(all_data, llm_results)):
                true_label = 1 if rec.get('is_toxic') else 0
                if isinstance(res, Exception):
                    update_llm_result(rec['id'], -1, 0, [])
                else:
                    llm_pred = int(res.get('is_toxic', False))
                    llm_time = res.get('time_cost', 0)
                    llm_spans = res.get('toxic_spans', [])
                    # 保留原有 DFA 结果
                    df = get_all_results()
                    existing = df[df['text_id'] == rec['id']]
                    dfa_pred = existing['dfa_pred'].values[0] if not existing.empty else -1
                    dfa_hit_words = json.loads(
                        existing['hit_words'].values[0]) if not existing.empty and existing['hit_words'].values[0] else []
                    save_result(rec['id'], true_label, dfa_pred,
                                llm_pred, dfa_hit_words, 0, llm_time, llm_spans)
            st.success("LLM 扫描完成")

    with col_btn3:
        if st.button("⚡ 同时 DFA+LLM", disabled=not api_ready):
            scanner = DFAScanner('sensitive_words.txt')
            # DFA 先全部扫描
            for rec in all_data:
                text = rec['text']
                dfa_hit, dfa_words = scanner.scan(text)
                true_label = 1 if rec.get('is_toxic') else 0
                save_result(rec['id'], true_label, int(
                    dfa_hit), -1, dfa_words, 0, 0, [])
            # LLM 扫描
            tasks = [(llm_scan, (rec['text'], api_key, base_url, llm_model))
                     for rec in all_data]
            progress_bar = st.progress(0)
            llm_results = run_concurrently(
                tasks,
                max_workers=concurrency,
                progress_placeholder=progress_bar,
                progress_text="同步扫描中"
            )
            for i, (rec, res) in enumerate(zip(all_data, llm_results)):
                req = all_data[i]
                true_label = 1 if req.get('is_toxic') else 0
                if isinstance(res, Exception):
                    llm_pred = -1
                    llm_spans = []
                    llm_time = 0
                else:
                    llm_pred = int(res.get('is_toxic', False))
                    llm_spans = res.get('toxic_spans', [])
                    llm_time = res.get('time_cost', 0)
                # 获取 DFA 结果
                df = get_all_results()
                row = df[df['text_id'] == rec['id']]
                dfa_pred = row['dfa_pred'].values[0] if not row.empty else -1
                dfa_hit_words = json.loads(
                    row['hit_words'].values[0]) if not row.empty and row['hit_words'].values[0] else []
                save_result(rec['id'], true_label, dfa_pred,
                            llm_pred, dfa_hit_words, 0, llm_time, llm_spans)
            st.success("全部扫描完成")

    # ----- 样本状态总览 -----
    st.markdown("---")
    st.subheader("样本检测状态")
    df_all = get_all_results()
    if not df_all.empty:
        def status(dfa, llm):
            dfa_str = "✔️" if dfa == 1 else ("✖️" if dfa == 0 else "⬜")
            llm_str = "✔️" if llm == 1 else ("✖️" if llm == 0 else "⬜")
            return f"{dfa_str} / {llm_str}"
        df_all['status'] = df_all.apply(
            lambda r: status(r['dfa_pred'], r['llm_pred']), axis=1)
        st.dataframe(
            df_all[['text_id', 'true_label', 'status']], use_container_width=True)

    # ----- 样本详情查看（快速切换）-----
    st.markdown("---")
    st.subheader("🔍 样本深度对比")
    if not df_all.empty:
        sample_ids = df_all['text_id'].tolist()
        selected_id = st.selectbox("选择样本", sample_ids)
        if selected_id:
            rec = next((r for r in all_data if r['id'] == selected_id), None)
            if rec is None:
                st.warning("样本数据丢失")
            else:
                db_row = df_all[df_all['text_id'] == selected_id].iloc[0]
                original = rec.get('original_text', '（无原文）')
                toxic_text = rec.get('text', '')
                true_spans = rec.get('toxic_spans', [])
                strategy = rec.get('attack_strategy', '未知')
                dfa_pred = db_row['dfa_pred']
                llm_pred = db_row['llm_pred']
                dfa_words = json.loads(
                    db_row['hit_words']) if db_row['hit_words'] else []
                llm_spans = json.loads(
                    db_row['llm_spans']) if db_row['llm_spans'] else []

                # 视图1：原文
                st.markdown("**📄 原始文本**")
                st.info(original)

                # 视图2：投毒文本 + 预设毒点（黄色标记）
                st.markdown("---")
                st.markdown(f"**🦠 投毒文本（策略：{strategy}）**")
                annotated_true = highlight_toxic(toxic_text, true_spans)
                annotated_true = annotated_true.replace(
                    'style="background-color:#ff4d4d', 'style="background-color:#ffc107; color:black')
                st.markdown(annotated_true, unsafe_allow_html=True)
                st.caption(f"预设毒点：{true_spans}")

                # 视图3：双防检测结果
                st.markdown("---")
                st.markdown("**🛡️ 防火墙检测结果（完全盲测）**")
                col_d, col_l = st.columns(2)
                with col_d:
                    st.subheader("一防 DFA")
                    if dfa_pred == -1:
                        st.info("未检测")
                    elif dfa_pred == 1:
                        st.error(
                            f"命中毒点：{', '.join(dfa_words) if dfa_words else '（空）'}")
                    else:
                        st.success("安全")
                    dfa_hl = highlight_toxic(toxic_text, dfa_words)
                    st.markdown(dfa_hl, unsafe_allow_html=True)

                with col_l:
                    st.subheader("二防 LLM")
                    if llm_pred == -1:
                        st.info("未检测")
                    elif llm_pred == 1:
                        st.error(
                            f"命中毒点：{', '.join(llm_spans) if llm_spans else '（空）'}")
                    else:
                        st.success("安全")
                    llm_hl = highlight_toxic(toxic_text, llm_spans)
                    st.markdown(llm_hl, unsafe_allow_html=True)

                # 命中分析（只要有一方检测过就显示）
                if dfa_pred != -1 or llm_pred != -1:
                    st.markdown("---")
                    st.subheader("📊 检测效果分析（命中 vs 预设毒点）")
                    true_set = set(true_spans)
                    dfa_set = set(dfa_words)
                    llm_set = set(llm_spans)

                    # DFA 分析（带子串匹配）
                    dfa_hits = {t for t in true_set if t in dfa_words}
                    remaining_dfa = true_set - dfa_hits
                    for t in remaining_dfa:
                        if any(t in d for d in dfa_words) or any(d in t for d in dfa_words):
                            dfa_hits.add(t)
                    dfa_miss = true_set - dfa_hits
                    dfa_extra = dfa_set - true_set

                    # LLM 分析（带子串匹配）
                    llm_hits = {t for t in true_set if t in llm_spans}
                    remaining_llm = true_set - llm_hits
                    for t in remaining_llm:
                        if any(t in l for l in llm_spans) or any(l in t for l in llm_spans):
                            llm_hits.add(t)
                    llm_miss = true_set - llm_hits
                    llm_extra = llm_set - true_set

                    col_a1, col_a2 = st.columns(2)
                    with col_a1:
                        st.markdown("**DFA**")
                        st.write(f"✅ 命中：{list(dfa_hits) if dfa_hits else '无'}")
                        st.write(f"❌ 漏报：{list(dfa_miss) if dfa_miss else '无'}")
                        st.write(
                            f"⚠️ 额外检出：{list(dfa_extra) if dfa_extra else '无'}")
                    with col_a2:
                        st.markdown("**LLM**")
                        st.write(f"✅ 命中：{list(llm_hits) if llm_hits else '无'}")
                        st.write(f"❌ 漏报：{list(llm_miss) if llm_miss else '无'}")
                        st.write(
                            f"⚠️ 额外检出：{list(llm_extra) if llm_extra else '无'}")
                else:
                    st.info("请先至少运行一次检测")
    else:
        st.info("暂无检测数据，请先点击任一扫描按钮")

# ================= Tab3: 可视化分析 =================
with tab3:
    st.header("检测结果统计")
    df = get_all_results()
    if not df.empty:
        df['final_pred'] = ((df['dfa_pred'] == 1) | (
            df['llm_pred'] == 1)).astype(int)
        total = len(df)
        tp = len(df[(df['true_label'] == 1) & (df['final_pred'] == 1)])
        tn = len(df[(df['true_label'] == 0) & (df['final_pred'] == 0)])
        fp = len(df[(df['true_label'] == 0) & (df['final_pred'] == 1)])
        fn = len(df[(df['true_label'] == 1) & (df['final_pred'] == 0)])

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("总样本", total)
        col2.metric("正确拦截 (TP)", tp)
        col3.metric("漏报 (FN)", fn)
        col4.metric("误报 (FP)", fp)

        fig1 = px.pie(names=['有毒', '无毒'], values=[df['true_label'].sum(), total - df['true_label'].sum()],
                      title="测试集真实标签分布")
        st.plotly_chart(fig1, use_container_width=True)

        dfa_hit = df['dfa_pred'].sum()
        llm_hit = df['llm_pred'].sum()
        fig2 = px.bar(x=['一防 DFA', '二防 LLM'], y=[dfa_hit, llm_hit],
                      labels={'x': '防火墙', 'y': '命中数'}, title="防火墙拦截数量对比")
        st.plotly_chart(fig2, use_container_width=True)

        with st.expander("查看完整数据库记录"):
            st.dataframe(df)
    else:
        st.warning("暂无检测数据，请先运行检测")
