import streamlit as st
import feedparser
import sqlite3
import pandas as pd
import datetime
import random

# --- 設定頁面 ---
st.set_page_config(page_title="Bio-Science Reader", layout="wide")

# --- 🎨 護眼模式 (Google Style Dark Mode) ---
def apply_google_dark_mode():
    st.markdown("""
        <style>
        /* 1. 整體背景 - Google Dark Grey */
        .stApp {
            background-color: #202124;
        }
        
        /* 2. 側邊欄背景 */
        section[data-testid="stSidebar"] {
            background-color: #171717; 
        }

        /* 3. 文字顏色 - Google Off-white */
        h1, h2, h3, h4, h5, h6, p, li, label, .stMarkdown, .stText {
            color: #E8EAED !important;
        }
        
        /* 4. 連結顏色 - Google Blue */
        a {
            color: #8AB4F8 !important;
        }

        /* 5. 卡片/容器背景 - Google Surface Color */
        /* 針對 st.container(border=True) 的樣式覆寫 */
        div[data-testid="stVerticalBlockBorderWrapper"] > div {
            background-color: #303134;
            border-color: #3c4043;
        }
        
        /* 6. 按鈕樣式微調 */
        button {
            border-color: #5f6368 !important;
            color: #E8EAED !important;
        }
        button:hover {
            border-color: #8AB4F8 !important;
            color: #8AB4F8 !important;
        }
        
        /* 7. 表格/Dataframe 文字修正 */
        div[data-testid="stDataFrame"] {
            background-color: #303134; 
        }
        </style>
    """, unsafe_allow_html=True)

# --- 資料庫處理 (SQLite) ---
def init_db():
    conn = sqlite3.connect('reading_log.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date DATE,
            title TEXT,
            category TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS vocabulary (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date DATE,
            word TEXT,
            meaning TEXT,
            note TEXT
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
    st.sidebar.success(f"已儲存：{word}")

def get_reading_stats():
    conn = sqlite3.connect('reading_log.db')
    df = pd.read_sql_query("SELECT date, count(*) as count FROM logs GROUP BY date ORDER BY date", conn)
    conn.close()
    return df

def get_vocab_list():
    conn = sqlite3.connect('reading_log.db')
    df = pd.read_sql_query("SELECT date as '日期', word as '單字', meaning as '中文意思', note as '備註' FROM vocabulary ORDER BY id DESC", conn)
    conn.close()
    return df

# --- 抓取文章功能 ---
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

    # --- 側邊欄 ---
    with st.sidebar:
        st.header("⚙️ 設定")
        
        # [NEW] 護眼模式開關
        # 預設為 False (亮色模式)，開啟則變為 True
        dark_mode = st.toggle("🌙 護眼模式 (Google Dark)", value=False)
        if dark_mode:
            apply_google_dark_mode()

        st.divider()
        
        st.header("📝 單字筆記本")
        with st.form("vocab_form", clear_on_submit=True):
            input_word = st.text_input("英文單字")
            input_meaning = st.text_input("中文意思")
            input_note = st.text_area("備註", height=80)
            submitted = st.form_submit_button("💾 儲存")
            if submitted and input_word:
                add_vocab(input_word, input_meaning, input_note)
        
        st.markdown("---")
        st.caption("Daily Bio-Science Reader")

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
            # 使用 container 讓卡片更明顯
            with st.container(border=True):
                st.subheader(article['title'])
                st.caption(f"🏷️ {article['category']}")
                st.write(article['summary'])
                st.markdown(f"[👉 閱讀全文]({article['link']})")
                
                # 按鈕
                if st.button(f"✅ 完成", key=f"btn_{i}", use_container_width=True):
                    log_reading(article['title'], article['category'])
                    st.rerun()

    st.divider()

    # 2. 數據與單字庫區塊
    tab1, tab2 = st.tabs(["📈 累積成就圖表", "🔤 我的單字庫"])

    with tab1:
        df_stats = get_reading_stats()
        if not df_stats.empty:
            df_stats['date'] = pd.to_datetime(df_stats['date'])
            df_stats['cumulative'] = df_stats['count'].cumsum()
            st.area_chart(df_stats, x='date', y='cumulative', color="#8AB4F8") # 改用 Google Blue
            st.metric("總閱讀篇數", df_stats['count'].sum())
        else:
            st.info("尚無閱讀紀錄，加油！")

    with tab2:
        df_vocab = get_vocab_list()
        if not df_vocab.empty:
            st.dataframe(
                df_vocab, 
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("側邊欄可以新增單字喔！")

if __name__ == "__main__":
    main()
