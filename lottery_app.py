# lottery_app.py (Final Confirmed Version)

import streamlit as st
import pandas as pd
import random

def run_single_lottery_pool(registrations_pool_df, previous_winners_set, num_to_draw, pinned_players_in_pool, name_column):
    """
    对一个给定的、已经筛选好的池子执行一次抽签的核心函数。
    """
    current_registrants = set(registrations_pool_df[name_column].unique())
    
    # 特殊情况处理：验证指定人员
    invalid_pinned = [p for p in pinned_players_in_pool if p not in current_registrants]
    if invalid_pinned:
        return pd.DataFrame(), f"指定人员 {', '.join(invalid_pinned)} 未在当前池中找到。"
    if len(pinned_players_in_pool) > num_to_draw:
        return pd.DataFrame(), f"指定人数 ({len(pinned_players_in_pool)}) 超过了抽取名额 ({num_to_draw})。"

    # 初始化，优先放入指定人员
    final_winners = list(pinned_players_in_pool)
    num_remaining_to_draw = num_to_draw - len(final_winners)

    if num_remaining_to_draw <= 0:
        winners_df = registrations_pool_df[registrations_pool_df[name_column].isin(final_winners)].drop_duplicates(subset=[name_column])
        return winners_df, "所有名额已由指定人员填补。"

    pool = current_registrants - set(final_winners)
    
    # 划分优先级池：优先新人，备用往期人员
    eligible_pool = list(pool - previous_winners_set)
    random.shuffle(eligible_pool)
    
    backup_pool = list(pool.intersection(previous_winners_set))
    random.shuffle(backup_pool)

    # 执行抽签
    drawn_from_eligible = eligible_pool[:num_remaining_to_draw]
    final_winners.extend(drawn_from_eligible)
    num_still_to_draw = num_to_draw - len(final_winners)

    # 特殊情况处理：新人不足，从备用池补抽
    if num_still_to_draw > 0:
        drawn_from_backup = backup_pool[:num_still_to_draw]
        final_winners.extend(drawn_from_backup)

    final_df = registrations_pool_df[registrations_pool_df[name_column].isin(final_winners)].drop_duplicates(subset=[name_column]).reset_index(drop=True)
    return final_df, "成功"


def run_lottery_by_class(registrations_df, previous_winners_df, num_per_class, pinned_players, name_column, class_column):
    """
    按班型分组进行抽签的总控函数。
    """
    # 特殊情况处理：验证列名是否存在
    if name_column not in registrations_df.columns or name_column not in previous_winners_df.columns:
        return pd.DataFrame(), f"❌ **错误**: 姓名列 '{name_column}' 未在两个文件中同时找到。"
    if class_column not in registrations_df.columns:
        return pd.DataFrame(), f"❌ **错误**: 班型列 '{class_column}' 未在报名表中找到。"

    # 数据清洗：去空格、去空行
    for df in [registrations_df, previous_winners_df]:
        df[name_column] = df[name_column].astype(str).str.strip()
        df.dropna(subset=[name_column], inplace=True)
        df.drop(df[df[name_column] == ''].index, inplace=True)
    registrations_df[class_column] = registrations_df[class_column].astype(str).str.strip()

    previous_winners_set = set(previous_winners_df[name_column].unique())
    pinned_players_set = {p.strip() for p in pinned_players if p.strip()}
    
    # 按班型循环抽签
    all_class_types = registrations_df[class_column].unique()
    all_winners_list = []
    summary_messages = []

    for class_type in all_class_types:
        st.write(f"--- \n**正在为【{class_type}】抽签...**")
        
        class_registrations_df = registrations_df[registrations_df[class_column] == class_type]
        
        # 自动将在该班报名的指定人员加入
        pinned_players_in_class = list(pinned_players_set.intersection(set(class_registrations_df[name_column])))
        
        winners_df, status = run_single_lottery_pool(
            class_registrations_df,
            previous_winners_set,
            num_per_class,
            pinned_players_in_class,
            name_column
        )
        
        if not winners_df.empty:
            all_winners_list.append(winners_df)
            summary_messages.append(f"✔️ **{class_type}**: 成功抽出 **{len(winners_df)}** 人 (目标 {num_per_class} 人)。")
            st.dataframe(winners_df)
        else:
            summary_messages.append(f"❌ **{class_type}**: 抽签失败或无报名者。状态: {status}")

    if not all_winners_list:
        return pd.DataFrame(), "所有班型均未能抽出任何人员。"
        
    final_results_df = pd.concat(all_winners_list, ignore_index=True)
    return final_results_df, "\n".join(summary_messages)


# --- Streamlit 应用界面 ---
st.set_page_config(page_title="分班抽签器", layout="wide")

st.title("🎾 网球训练活动 · 按班型抽签器")
st.markdown("此版本将为**每个班型**独立进行抽签，并已内置多种特殊情况处理逻辑。")
st.markdown("---")

with st.sidebar:
    st.header("⚙️ 抽签设置")
    num_per_class = st.number_input("1. 每个班型抽取人数", min_value=1, value=8, step=1)
    pinned_players_str = st.text_area(
        "2. (可选) 指定中签人员 (全局)",
        help="在此处输入的名字将必定中签，程序会自动将其分配到其报名的班级。",
        placeholder="张三\n李四\n..."
    )
    st.markdown("---")
    st.header("🔧 高级设置")
    name_column = st.text_input("3. 指定姓名列的列名", value="姓名")
    class_column = st.text_input("4. 指定班型列的列名", value="班型")

st.header("📂 文件上传")
st.info(f"请确保报名表包含 **'{name_column}'** 和 **'{class_column}'** 两列。")

col1, col2 = st.columns(2)
with col1:
    registrations_file = st.file_uploader("⬆️ **上传最新的报名表**", type=['csv', 'xlsx'])
with col2:
    previous_winners_file = st.file_uploader("⬆️ **上传上一次的中签名单**", type=['csv', 'xlsx'])

st.markdown("---")

if st.button("🚀 **按班型开始抽签**", use_container_width=True, type="primary"):
    if registrations_file and previous_winners_file:
        try:
            read_file = lambda file: pd.read_excel(file) if file.name.endswith('.xlsx') else pd.read_csv(file)
            registrations_df = read_file(registrations_file)
            previous_winners_df = read_file(previous_winners_file)

            pinned_players = pinned_players_str.strip().split('\n')
            
            st.header("抽签进行中...")
            final_winners_df, summary_message = run_lottery_by_class(
                registrations_df, 
                previous_winners_df, 
                num_per_class, 
                pinned_players,
                name_column,
                class_column
            )
            
            st.header("🎉 抽签完成")
            st.success("总览信息:")
            st.text(summary_message)

            if not final_winners_df.empty:
                st.subheader("最终总名单")
                st.dataframe(final_winners_df, use_container_width=True)
                
                csv_output = final_winners_df.to_csv(index=False).encode('utf-8-sig')
                
                st.download_button(
                    label="📥 下载最终总名单 (.csv)",
                    data=csv_output,
                    file_name=f"各班型中签总名单_{pd.Timestamp.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )

        except Exception as e:
            st.error(f"处理文件时发生意外错误: {e}")
            st.warning("请检查文件格式是否正确，并确保指定的姓名列和班型列都存在。")
    else:
        st.warning("⚠️ 请务必上传 **报名表** 和 **上期中签名单** 两个文件。")