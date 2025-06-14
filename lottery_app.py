# lottery_app.py

import streamlit as st
import pandas as pd
import random

def run_lottery(registrations_df, previous_winners_df, num_to_draw, pinned_players, name_column):
    """
    运行抽签逻辑的核心函数。

    Args:
        registrations_df (pd.DataFrame): 包含最新报名信息的DataFrame。
        previous_winners_df (pd.DataFrame): 包含上期中签者信息的DataFrame。
        num_to_draw (int): 需要抽取的总人数。
        pinned_players (list): 必须中签的人员名单。
        name_column (str): 在DataFrame中代表姓名的列名。

    Returns:
        tuple: (最终中签名单DataFrame, 状态信息字符串)
    """
    # --- 1. 数据准备与验证 ---
    if name_column not in registrations_df.columns or name_column not in previous_winners_df.columns:
        return pd.DataFrame(), f"❌ **错误**: 指定的列名 '{name_column}' 未在两个上传文件中同时找到。"

    # --- 2. 数据清洗 ---
    # 统一转换为字符串并去除首尾空格
    for df in [registrations_df, previous_winners_df]:
        df[name_column] = df[name_column].astype(str).str.strip()
        # 删除清洗后为空的行
        df.dropna(subset=[name_column], inplace=True)
        df.drop(df[df[name_column] == ''].index, inplace=True)

    current_registrants = set(registrations_df[name_column].unique())
    previous_winners = set(previous_winners_df[name_column].unique())

    # --- 3. 验证指定人员和抽签人数 ---
    pinned_players = [p.strip() for p in pinned_players if p.strip()]
    invalid_pinned = [p for p in pinned_players if p not in current_registrants]
    if invalid_pinned:
        return pd.DataFrame(), f"❌ **错误**: 以下指定人员未在本次报名表中找到: {', '.join(invalid_pinned)}"

    if len(pinned_players) > num_to_draw:
        return pd.DataFrame(), "❌ **错误**: 指定中签人数不能超过抽签总人数。"

    # --- 4. 初始化抽签池 ---
    final_winners = list(pinned_players)
    num_remaining_to_draw = num_to_draw - len(final_winners)

    if num_remaining_to_draw <= 0:
        winners_df = registrations_df[registrations_df[name_column].isin(final_winners)].drop_duplicates(subset=[name_column])
        return winners_df, "✅ 所有名额已由指定人员填补。"

    # 抽签池排除已指定的玩家
    pool = current_registrants - set(final_winners)
    
    # --- 5. 划分优先级池并随机排序 ---
    # 优先池: 未中过签的新人
    eligible_pool = list(pool - previous_winners)
    random.shuffle(eligible_pool)
    
    # 备用池: 报名了本次活动, 但上次也中签了的人
    backup_pool = list(pool.intersection(previous_winners))
    random.shuffle(backup_pool)

    # --- 6. 执行抽签 ---
    status_message = ""
    # 从优先池抽取
    drawn_from_eligible = eligible_pool[:num_remaining_to_draw]
    final_winners.extend(drawn_from_eligible)
    
    num_still_to_draw = num_to_draw - len(final_winners)

    # --- 7. 处理特殊情况 (人数不足) ---
    if num_still_to_draw > 0:
        # 从备用池补抽
        drawn_from_backup = backup_pool[:num_still_to_draw]
        final_winners.extend(drawn_from_backup)
        
        message_parts = [
            f"⚠️ **注意**: 新报名人数不足。",
            f"已从新报名者中选出 **{len(drawn_from_eligible)}** 人。",
        ]
        if drawn_from_backup:
            message_parts.append(f"并从往期参与者中补充了 **{len(drawn_from_backup)}** 人。")
        status_message = " ".join(message_parts)
    
    if len(final_winners) < num_to_draw:
        status_message += f"\n\n**警告**: 总报名人数 ({len(current_registrants)}) 少于计划抽签人数 ({num_to_draw})。无法抽满名额。"

    # --- 8. 生成最终结果 ---
    final_df = registrations_df[registrations_df[name_column].isin(final_winners)].drop_duplicates(subset=[name_column]).reset_index(drop=True)
    return final_df, status_message or f"✅ **成功**: 已成功抽出 **{len(final_df)}** 人！"


# --- Streamlit 应用界面 ---
st.set_page_config(page_title="智能抽签器", layout="wide")

st.title("🎾 网球训练活动 · 智能抽签器")
st.markdown("一个公平、透明且能处理特殊情况的随机抽签工具。")
st.markdown("---")

# --- 侧边栏设置 ---
with st.sidebar:
    st.header("⚙️ 抽签设置")
    num_to_draw = st.number_input("1. 本次抽取总人数", min_value=1, value=10, step=1)
    pinned_players_str = st.text_area(
        "2. (可选) 指定中签人员",
        help="每行输入一个姓名。在此处输入的名字将必定中签。",
        placeholder="张三\n李四\n..."
    )
    st.markdown("---")
    st.header("🔧 高级设置")
    name_column = st.text_input("3. 指定包含姓名的列名", value="姓名")

# --- 主页面内容 ---
st.header("📂 文件上传")
st.info(f"请确保两个文件中都包含名为 **'{name_column}'** 的列。支持 `.csv` 和 `.xlsx` 格式。")

col1, col2 = st.columns(2)
with col1:
    registrations_file = st.file_uploader("⬆️ **上传最新的报名表**", type=['csv', 'xlsx'])
with col2:
    previous_winners_file = st.file_uploader("⬆️ **上传上一次的中签名单**", type=['csv', 'xlsx'])

st.markdown("---")

if st.button("🚀 **开始抽签**", use_container_width=True, type="primary"):
    if registrations_file and previous_winners_file:
        try:
            read_file = lambda file: pd.read_excel(file) if file.name.endswith('.xlsx') else pd.read_csv(file)
            registrations_df = read_file(registrations_file)
            previous_winners_df = read_file(previous_winners_file)

            pinned_players = pinned_players_str.strip().split('\n')
            
            # --- 运行核心逻辑 ---
            final_winners_df, message = run_lottery(
                registrations_df, 
                previous_winners_df, 
                num_to_draw, 
                pinned_players,
                name_column
            )

            # --- 显示结果 ---
            st.header("🎉 抽签结果")
            if "错误" in message:
                st.error(message)
            elif "注意" in message or "警告" in message:
                st.warning(message)
            else:
                st.success(message)

            if not final_winners_df.empty:
                st.dataframe(final_winners_df, use_container_width=True)
                
                csv_output = final_winners_df.to_csv(index=False).encode('utf-8-sig')
                
                st.download_button(
                    label="📥 下载中签名单 (.csv)",
                    data=csv_output,
                    file_name=f"中签名单_{pd.Timestamp.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )

        except Exception as e:
            st.error(f"处理文件时发生意外错误: {e}")
            st.warning("请检查文件格式是否正确，并确保指定的姓名列存在。")
    else:
        st.warning("⚠️ 请务必上传 **报名表** 和 **上期中签名单** 两个文件。")