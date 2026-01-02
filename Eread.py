import streamlit as st
import feedparser
import sqlite3
import pandas as pd
import datetime
import random

# --- 設定頁面 ---
st.set_page_config(page_title="Bio-Science Reader", layout="wide")


# --- 資料庫處理 (SQLite) ---
def init_db():
    conn = sqlite3.connect('reading_log.db')
    c = conn.cursor()
    # 1. 閱讀紀錄表
    c.execute('''
              CREATE TABLE IF NOT EXISTS logs
              (
                  id
                  INTEGER
                  PRIMARY
                  KEY
                  AUTOINCREMENT,
                  date
                  DATE,
                  title
                  TEXT,
                  category
                  TEXT
              )
              ''')
    # 2. 單字庫表 (新功能)
    c.execute('''
              CREATE TABLE IF NOT EXISTS vocabulary
              (
                  id
                  INTEGER
                  PRIMARY
                  KEY
                  AUTOINCREMENT,
                  date
                  DATE,
                  word
                  TEXT,
                  meaning
                  TEXT,
                  note
                  TEXT
              )
              ''')
    conn.commit()
    conn.close()


def log_reading(title, category):
    conn = sqlite3.connect('reading_log.db')
    c = conn.cursor()
    today = datetime.date.today()
    c.execute('INSERT INTO logs (date, title, category) VALUES (?, ?, ?)', (today, title, category))
    conn.commit()
    conn.close()
    st.success(f"已記錄閱讀：{title}")


def add_vocab(word, meaning, note):
    conn = sqlite3.connect('reading_log.db')
    c = conn.cursor()
    today = datetime.date.today()
    c.execute('INSERT INTO vocabulary (date, word, meaning, note) VALUES (?, ?, ?, ?)', (today, word, meaning, note))
    conn.commit()
    conn.close()
    st.sidebar.success(f"已儲存單字：{word}")


def get_reading_stats():
    conn = sqlite3.connect('reading_log.db')
    df = pd.read_sql_query("SELECT date, count(*) as count FROM logs GROUP BY date ORDER BY date", conn)
    conn.close()
    return df


def get_vocab_list():
    conn = sqlite3.connect('reading_log.db')
    # 讀取單字，按日期倒序排列（最新的在最上面）
    df = pd.read_sql_query(
        "SELECT date as '日期', word as '單字', meaning as '中文意思', note as '備註' FROM vocabulary ORDER BY id DESC",
        conn)
    conn.close()
    return df


# --- 抓取文章功能 (維持不變) ---
def get_articles():
    rss_urls = [
        ('Biology', 'https://www.sciencedaily.com/rss/plants_animals/biology.xml'),
        ('Health', 'https://www.sciencedaily.com/rss/health_medicine.xml'),
        ('Science', 'https://www.sciencedaily.com/rss/top/science.xml')
    ]
    articles = []
    for category, url in rss_urls:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:3]:
                articles.append({
                    'title': entry.title,
                    'link': entry.link,
                    'summary': entry.summary,
                    'category': category,
                    'published': entry.get('published', 'Unknown')
                })
        except:
            continue

    if len(articles) >= 3:
        return random.sample(articles, 3)
    else:
        return articles


# --- 主程式邏輯 ---
def main():
    init_db()

    # --- 側邊欄：單字筆記本 ---
    with st.sidebar:
        st.header("📝 單字筆記本")
        st.write("閱讀時遇到不會的字？記下來！")

        with st.form("vocab_form", clear_on_submit=True):
            input_word = st.text_input("英文單字 (Word)")
            input_meaning = st.text_input("中文意思 (Meaning)")
            input_note = st.text_area("例句或備註 (Optional)", height=100)

            submitted = st.form_submit_button("💾 儲存單字")
            if submitted and input_word and input_meaning:
                add_vocab(input_word, input_meaning, input_note)
            elif submitted:
                st.warning("請至少輸入單字和意思！")

        st.markdown("---")
        st.caption("Keep learning, step by step.")

    # --- 主畫面 ---
    st.title("🧬 Daily Bio-Science Reader")
    st.markdown("每天 3 篇，累積科學閱讀量，擴充單字庫！")
    st.divider()

    # 1. 文章區塊
    st.header("📖 今日閱讀任務")
    if 'articles' not in st.session_state:
        st.session_state.articles = get_articles()

    cols = st.columns(3)
    for i, article in enumerate(st.session_state.articles):
        with cols[i]:
            with st.container(border=True):  # 加個邊框比較好看
                st.subheader(article['title'])
                st.caption(f"🏷️ {article['category']}")
                st.write(article['summary'])
                st.markdown(f"[👉 閱讀全文]({article['link']})")
                if st.button(f"✅ 完成", key=f"btn_{i}", use_container_width=True):
                    log_reading(article['title'], article['category'])
                    st.rerun()

    st.divider()

    # 2. 數據與單字庫區塊 (分成兩個分頁顯示，比較整潔)
    tab1, tab2 = st.tabs(["📈 累積成就圖表", "🔤 我的單字庫"])

    with tab1:
        df_stats = get_reading_stats()
        if not df_stats.empty:
            df_stats['date'] = pd.to_datetime(df_stats['date'])
            df_stats['cumulative'] = df_stats['count'].cumsum()
            st.area_chart(df_stats, x='date', y='cumulative', color="#4CAF50")
            st.metric("總閱讀篇數", df_stats['count'].sum())
        else:
            st.info("尚無閱讀紀錄，加油！")

    with tab2:
        df_vocab = get_vocab_list()
        if not df_vocab.empty:
            # 使用 Dataframe 顯示，支援排序和搜尋
            st.dataframe(
                df_vocab,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "日期": st.column_config.DateColumn("紀錄日期", format="YYYY-MM-DD"),
                    "單字": st.column_config.TextColumn("Word", width="medium"),
                    "中文意思": st.column_config.TextColumn("Meaning", width="medium"),
                    "備註": st.column_config.TextColumn("Notes", width="large"),
                }
            )
        else:
            st.info("側邊欄可以新增單字喔！目前單字庫是空的。")


if __name__ == "__main__":
    main()