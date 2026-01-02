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
        .stApp { background-color: #202124; }
        section[data-testid="stSidebar"] { background-color: #171717; }
        h1, h2, h3, h4, h5, h6, p, li, label, .stMarkdown, .stText { color: #E8EAED !important; }
        a { color: #8AB4F8 !important; }
        div[data-testid="stVerticalBlockBorderWrapper"] > div { background-color: #303134; border-color: #3c4043; }
        button { border-color: #5f6368 !important; color: #E8EAED !important; }
        button:hover { border-color: #8AB4F8 !important; color: #8AB4F8 !important; }
        div[data-testid="stDataFrame"] { background-color: #303134; }
        </style>
    """, unsafe_allow_html=True)

# --- 資料庫處理 (SQLite) ---
def init_db():
    conn = sqlite3.connect('reading_log.db')
    c = conn.cursor()
    # 1. 閱讀紀錄表
    c.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date DATE,
            title TEXT,
            category TEXT
        )
    ''')
    # 2. 單字庫表
    c.execute('''
        CREATE TABLE IF NOT EXISTS vocabulary (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date DATE,
            word TEXT,
            meaning TEXT,
            note TEXT
        )
    ''')
    # 3. [NEW] 每日固定文章表
    # 用來儲存每天系統挑選的那 3 篇，確保當天不會變
    c.execute('''
        CREATE TABLE IF NOT EXISTS daily_articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date DATE,
            title TEXT,
            link TEXT,
            summary TEXT,
            category TEXT,
            published TEXT
        )
    ''')
    conn.commit()
    conn.close()

# --- 資料庫操作功能 ---
def log_reading(title, category):
    conn = sqlite3.connect('reading_log.db')
    c = conn.cursor()
    today = datetime.date.today()
    # 避免重複打卡同一篇 (選擇性功能)
    c.execute("SELECT * FROM logs WHERE date = ? AND title = ?", (today, title))
    if not c.fetchone():
        c.execute('INSERT INTO logs (date, title, category) VALUES (?, ?, ?)', (today, title, category))
        conn.commit()
        st.success(f"已記錄閱讀：{title}")
    else:
        st.warning(f"這篇今天已經讀過囉：{title}")
    conn.close()

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

# --- [核心修改] 取得今日文章 (固定版) ---
def get_todays_articles_fixed():
    today = datetime.date.today()
    conn = sqlite3.connect('reading_log.db')
    c = conn.cursor()
    
    # 1. 先查資料庫：今天是否已經產生過文章？
    c.execute("SELECT title, link, summary, category, published FROM daily_articles WHERE date = ?", (today,))
    rows = c.fetchall()
    
    # 2. 如果資料庫有資料 (代表今天已經產生過了)，直接回傳這些文章
    if rows:
        conn.close()
        articles = []
        for row in rows:
            articles.append({
                'title': row[0],
                'link': row[1],
                'summary': row[2],
                'category': row[3],
                'published': row[4]
            })
        return articles

    # 3. 如果資料庫沒有資料 (代表是今天第一次開啟)，去抓 RSS 並隨機選 3 篇存入
    else:
        # --- 抓取 RSS 邏輯 ---
        rss_urls = [
            ('Biology', 'https://www.sciencedaily.com/rss/plants_animals/biology.xml'),
            ('Health', 'https://www.sciencedaily.com/rss/health_medicine.xml'),
            ('Science', 'https://www.sciencedaily.com/rss/top/science.xml')
        ]
        pool = []
        for category, url in rss_urls:
            try:
                feed = feedparser.parse(url)
                # 每個分類多抓一點 (前 5 篇) 來做隨機池
                for entry in feed.entries[:5]:
                    pool.append({
                        'title': entry.title,
                        'link': entry.link,
                        'summary': entry.summary,
                        'category': category,
                        'published': entry.get('published', 'Unknown')
                    })
            except:
                continue
        
        # 從池中隨機選 3 篇
        selected_articles = []
        if len(pool) >= 3:
            selected_articles = random.sample(pool, 3)
        else:
            selected_articles = pool
        
        # --- 存入資料庫 (綁定今天日期) ---
        for art in selected_articles:
            c.execute('''
                INSERT INTO daily_articles (date, title, link, summary, category, published)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (today, art['title'], art['link'], art['summary'], art['category'], art['published']))
        
        conn.commit()
        conn.close()
        return selected_articles

# --- 主程式邏輯 ---
def main():
    init_db()

    # --- 側邊欄 ---
    with st.sidebar:
        st.header("⚙️ 設定")
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
    st.markdown(f"**{datetime.date.today()}** 今日精選文章 (24小時內固定)")
    st.divider()

    # 1. 文章區塊 (使用新的固定函數)
    st.header("📖 今日閱讀任務")
    
    # 這裡直接呼叫函數，不再依賴 session_state 來「暫存」，
    # 因為現在是由資料庫來「永久儲存」今天的選擇。
    daily_articles = get_todays_articles_fixed()

    cols = st.columns(3)
    # 處理可能抓不到文章的情況
    if not daily_articles:
        st.error("無法取得文章，請檢查網路連線或稍後再試。")
    else:
        for i, article in enumerate(daily_articles):
            with cols[i]:
                with st.container(border=True):
                    st.subheader(article['title'])
                    st.caption(f"🏷️ {article['category']}")
                    st.write(article['summary'])
                    st.markdown(f"[👉 閱讀全文]({article['link']})")
                    
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
            st.area_chart(df_stats, x='date', y='cumulative', color="#8AB4F8")
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
