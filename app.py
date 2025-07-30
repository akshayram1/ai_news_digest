import streamlit as st
import requests
import openai
from datetime import datetime, timedelta
import json
import re
from typing import List, Dict, Any
import time
from urllib.parse import quote_plus
import feedparser
import os
from dotenv import load_dotenv
import logging


# Setup logging to both file and console
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))

file_handler = logging.FileHandler("app.log")
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))

logging.basicConfig(
    level=logging.INFO,
    handlers=[console_handler, file_handler]
)

# Load environment variables
load_dotenv()

# Configure page
st.set_page_config(
    page_title="AI News Digest Assistant",
    page_icon="📰",
    layout="wide"
)

class NewsDigestAssistant:
    def __init__(self, openai_api_key: str):
        self.openai_client = openai.OpenAI(api_key=openai_api_key)
        
    def search_news_rss(self, query: str, num_articles: int = 5) -> List[Dict[str, Any]]:
        """Search for news using Google News RSS feed"""
        logging.info(f"[search_news_rss] Called with query='{query}', num_articles={num_articles}")
        print(f"[search_news_rss] Called with query='{query}', num_articles={num_articles}")
        try:
            encoded_query = quote_plus(query)
            rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"
            feed = feedparser.parse(rss_url)
            articles = []
            for entry in feed.entries[:num_articles]:
                article = {
                    'title': entry.title,
                    'url': entry.link,
                    'published': entry.get('published', ''),
                    'source': entry.get('source', {}).get('title', 'Unknown'),
                    'summary': entry.get('summary', '')
                }
                articles.append(article)
            logging.info(f"[search_news_rss] Output: {json.dumps(articles, ensure_ascii=False)}")
            print(f"[search_news_rss] Output: {json.dumps(articles, ensure_ascii=False)}")
            return articles
        except Exception as e:
            logging.error(f"[search_news_rss] Error: {str(e)}")
            print(f"[search_news_rss] Error: {str(e)}")
            st.error(f"Error fetching news: {str(e)}")
            return []
    
    def search_news_newsapi(self, query: str, api_key: str, num_articles: int = 5) -> List[Dict[str, Any]]:
        """Search for news using NewsAPI"""
        logging.info(f"[search_news_newsapi] Called with query='{query}', api_key={'***' if api_key else None}, num_articles={num_articles}")
        print(f"[search_news_newsapi] Called with query='{query}', api_key={'***' if api_key else None}, num_articles={num_articles}")
        try:
            url = "https://newsapi.org/v2/everything"
            params = {
                'q': query,
                'apiKey': api_key,
                'language': 'en',
                'sortBy': 'publishedAt',
                'pageSize': num_articles
            }
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            articles = []
            for article in data.get('articles', []):
                articles.append({
                    'title': article.get('title', ''),
                    'url': article.get('url', ''),
                    'published': article.get('publishedAt', ''),
                    'source': article.get('source', {}).get('name', 'Unknown'),
                    'summary': article.get('description', '') or article.get('content', '')
                })
            logging.info(f"[search_news_newsapi] Output: {json.dumps(articles, ensure_ascii=False)}")
            print(f"[search_news_newsapi] Output: {json.dumps(articles, ensure_ascii=False)}")
            return articles
        except Exception as e:
            logging.error(f"[search_news_newsapi] Error: {str(e)}")
            print(f"[search_news_newsapi] Error: {str(e)}")
            st.error(f"Error fetching news from NewsAPI: {str(e)}")
            return []
    
    def summarize_article(self, article: Dict[str, Any]) -> Dict[str, Any]:
        """Summarize an article using OpenAI"""
        logging.info(f"[summarize_article] Called with article: {json.dumps(article, ensure_ascii=False)}")
        print(f"[summarize_article] Called with article: {json.dumps(article, ensure_ascii=False)}")
        try:
            prompt = f"""
            Please analyze and summarize the following news article:
            
            Title: {article['title']}
            Content: {article['summary'][:1000]}
            
            Provide a summary that includes:
            1. Core insight or main claim (1-2 sentences)
            2. Key named entities (companies, people, events, locations)
            3. Important details or implications
            
            Format your response as JSON with the following structure:
            {{
                "core_insight": "Main point of the article",
                "named_entities": ["entity1", "entity2", "entity3"],
                "key_details": "Important details and implications",
                "summary": "Complete 1-2 paragraph summary"
            }}
            """
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a professional news analyst. Provide concise, accurate summaries in valid JSON format."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500
            )
            summary_text = response.choices[0].message.content
            logging.info(f"[summarize_article] OpenAI response: {summary_text}")
            print(f"[summarize_article] OpenAI response: {summary_text}")
            # Try to parse JSON response
            try:
                summary_data = json.loads(summary_text)
            except json.JSONDecodeError:
                # Fallback if JSON parsing fails
                summary_data = {
                    "core_insight": "Summary unavailable",
                    "named_entities": [],
                    "key_details": "Details unavailable",
                    "summary": summary_text[:200] + "..."
                }
            logging.info(f"[summarize_article] Output: {json.dumps(summary_data, ensure_ascii=False)}")
            print(f"[summarize_article] Output: {json.dumps(summary_data, ensure_ascii=False)}")
            return summary_data
        except Exception as e:
            logging.error(f"[summarize_article] Error: {str(e)}")
            print(f"[summarize_article] Error: {str(e)}")
            st.error(f"Error summarizing article: {str(e)}")
            return {
                "core_insight": "Summary unavailable",
                "named_entities": [],
                "key_details": "Details unavailable",
                "summary": "Unable to generate summary"
            }
    
    def analyze_sentiment(self, text: str) -> str:
        """Analyze sentiment of text using OpenAI"""
        logging.info(f"[analyze_sentiment] Called with text: {text[:200]}")
        print(f"[analyze_sentiment] Called with text: {text[:200]}")
        try:
            prompt = f"""
            Analyze the sentiment of the following text and classify it as exactly one of: "Positive", "Negative", or "Neutral".
            
            Text: {text[:500]}
            
            Respond with only the sentiment classification (Positive, Negative, or Neutral).
            """
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a sentiment analysis expert. Respond with only one word: Positive, Negative, or Neutral."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=10
            )
            sentiment = response.choices[0].message.content.strip()
            logging.info(f"[analyze_sentiment] OpenAI response: {sentiment}")
            print(f"[analyze_sentiment] OpenAI response: {sentiment}")
            # Validate sentiment response
            valid_sentiments = ["Positive", "Negative", "Neutral"]
            if sentiment not in valid_sentiments:
                logging.info(f"[analyze_sentiment] Output: Neutral (invalid response)")
                print(f"[analyze_sentiment] Output: Neutral (invalid response)")
                return "Neutral"
            logging.info(f"[analyze_sentiment] Output: {sentiment}")
            print(f"[analyze_sentiment] Output: {sentiment}")
            return sentiment
        except Exception as e:
            logging.error(f"[analyze_sentiment] Error: {str(e)}")
            print(f"[analyze_sentiment] Error: {str(e)}")
            st.error(f"Error analyzing sentiment: {str(e)}")
            return "Neutral"
    
    def generate_digest(self, topic: str, articles_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate a comprehensive daily digest"""
        logging.info(f"[generate_digest] Called with topic='{topic}', articles_data={json.dumps(articles_data, ensure_ascii=False)}")
        print(f"[generate_digest] Called with topic='{topic}', articles_data={json.dumps(articles_data, ensure_ascii=False)}")
        try:
            # Count sentiments
            sentiment_counts = {"Positive": 0, "Negative": 0, "Neutral": 0}
            for article in articles_data:
                sentiment = article.get('sentiment', 'Neutral')
                sentiment_counts[sentiment] += 1
            # Generate digest content
            digest_date = datetime.now().strftime("%B %d, %Y")
            digest = {
                "title": f"Daily News Digest: {topic}",
                "date": digest_date,
                "topic": topic,
                "total_articles": len(articles_data),
                "sentiment_summary": sentiment_counts,
                "articles": articles_data
            }
            logging.info(f"[generate_digest] Output: {json.dumps(digest, ensure_ascii=False)}")
            print(f"[generate_digest] Output: {json.dumps(digest, ensure_ascii=False)}")
            return digest
        except Exception as e:
            logging.error(f"[generate_digest] Error: {str(e)}")
            print(f"[generate_digest] Error: {str(e)}")
            st.error(f"Error generating digest: {str(e)}")
            return {}


def main():
    st.markdown(
        """
        <style>
        .main-title {
            font-size: 2.8rem;
            font-weight: 800;
            color: #1a237e;
            letter-spacing: 1px;
            margin-bottom: 0.2em;
        }
        .subtitle {
            font-size: 1.3rem;
            color: #3949ab;
            margin-bottom: 1.5em;
        }
        .stButton>button {
            background: linear-gradient(90deg, #1a73e8 0%, #43cea2 100%);
            color: white;
            font-weight: bold;
            border-radius: 8px;
            border: none;
            padding: 0.7em 2em;
            font-size: 1.1em;
            box-shadow: 0 2px 8px rgba(26,115,232,0.08);
        }
        .stButton>button:hover {
            background: linear-gradient(90deg, #43cea2 0%, #1a73e8 100%);
            color: #fffde7;
        }
        .stTextInput>div>div>input {
            background: #f0f2f6;
            border-radius: 8px;
            border: 1.5px solid #1a73e8;
            font-size: 1.1em;
        }
        .stSlider>div>div>div>div {
            background: #e3f2fd;
        }
        .stSelectbox>div>div>div>div {
            background: #e3f2fd;
        }
        .stSidebar {
            background: #f5f7fa;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown('<div class="main-title">📰 AI-Powered News Digest Assistant</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Get summarized news with sentiment analysis on any topic of your choice!</div>', unsafe_allow_html=True)

    # ...existing code...
    if not os.path.exists('.env'):
        st.warning("⚠️ No .env file found!")
        with st.expander("📋 Quick Setup Instructions"):
            st.markdown("""
            **Create a `.env` file in your project directory with:**
            ```
            OPENAI_API_KEY=your_openai_key_here
            NEWS_API_KEY=your_news_api_key_here
            ```
            **Where to get API keys:**
            - **OpenAI**: [Get API key](https://platform.openai.com/api-keys) (Required)
            - **NewsAPI**: [Get free key](https://newsapi.org/register) (Optional - 1,000 requests/day free)
            **Then restart the Streamlit app.**
            """)
        st.markdown("---")

    openai_key = os.getenv("OPENAI_API_KEY")
    news_api_key = os.getenv("NEWS_API_KEY")

    with st.sidebar:
        st.markdown('<h2 style="color:#1a73e8;">⚙️ Configuration</h2>', unsafe_allow_html=True)
        st.subheader("🔑 API Key Status")
        if openai_key:
            st.success("✅ OpenAI API Key: Loaded from .env")
        else:
            st.error("❌ OpenAI API Key: Not found in .env")
            st.info("Add OPENAI_API_KEY to your .env file")
        if news_api_key:
            st.success("✅ NewsAPI Key: Loaded from .env")
        else:
            st.warning("⚠️ NewsAPI Key: Not found in .env")
            st.info("Add NEWS_API_KEY to your .env file (optional)")
        st.markdown("---")
        with st.expander("📝 Get Free News API Keys"):
            st.markdown("""
            **🆓 Free News API Sources:**
            1. **NewsAPI.org** (Recommended)
               - 🔗 [Get free key](https://newsapi.org/register)
               - ✅ 1,000 requests/day (free tier)
               - ✅ Real-time news from 80,000+ sources
               - ✅ Easy registration with email
            2. **GNews API**
               - 🔗 [Get free key](https://gnews.io/)
               - ✅ 100 requests/day (free tier)
               - ✅ Google News integration
            3. **NewsData.io**
               - 🔗 [Get free key](https://newsdata.io/)
               - ✅ 200 requests/day (free tier)
               - ✅ Multiple language support
            **📋 Setup Instructions:**
            1. Sign up for a free account
            2. Get your API key
            3. Add to `.env` file: `NEWS_API_KEY=your_key_here`
            4. Restart the Streamlit app
            """)
        st.markdown("---")
        available_sources = ["Google News RSS (Free)"]
        if news_api_key:
            available_sources.append("NewsAPI")
        news_source = st.selectbox(
            "News Source",
            available_sources,
            help="Choose your preferred news source"
        )
        num_articles = st.slider(
            "Number of Articles",
            min_value=3,
            max_value=10,
            value=5,
            help="Number of articles to include in the digest"
        )

    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown('<div style="font-size:1.3em;font-weight:600;color:#1a237e;">🔍 News Topic</div>', unsafe_allow_html=True)
        topic = st.text_input(
            "Enter your topic of interest:",
            placeholder="e.g., AI startups, stock market, climate change, cryptocurrency",
            help="Enter any topic you want to get news about"
        )
    with col2:
        st.markdown('<div style="font-size:1.3em;font-weight:600;color:#1a237e;">🚀 Generate Digest</div>', unsafe_allow_html=True)
        generate_btn = st.button(
            "✨ Generate News Digest",
            type="primary",
            use_container_width=True
        )

    if generate_btn:
        if not openai_key:
            st.error("❌ OpenAI API key not found. Please add OPENAI_API_KEY to your .env file.")
            st.info("Create a .env file in your project directory with: OPENAI_API_KEY=your_key_here")
            return
        if not topic:
            st.error("❌ Please enter a topic to search for.")
            return
        if news_source == "NewsAPI" and not news_api_key:
            st.error("❌ NewsAPI key not found. Please add NEWS_API_KEY to your .env file or use Google News RSS.")
            return
        assistant = NewsDigestAssistant(openai_key)
        progress_bar = st.progress(0)
        status_text = st.empty()
        try:
            status_text.text("🔍 Fetching news articles...")
            progress_bar.progress(20)
            if news_source == "NewsAPI":
                articles = assistant.search_news_newsapi(topic, news_api_key, num_articles)
                if not articles:
                    st.warning("⚠️ No relevant articles found with NewsAPI. Trying Google News RSS...")
                    articles = assistant.search_news_rss(topic, num_articles)
            else:
                articles = assistant.search_news_rss(topic, num_articles)
                if not articles and ' ' in topic:
                    st.warning("⚠️ No articles found with exact phrase. Trying broader search...")
                    broader_query = ' OR '.join(topic.split())
                    articles = assistant.search_news_rss(broader_query, num_articles)
            if not articles:
                st.error("❌ No articles found for the given topic. Please try a different search term.")
                return
            st.success(f"✅ Found {len(articles)} articles!")
            status_text.text("📝 Summarizing articles and analyzing sentiment...")
            progress_bar.progress(40)
            articles_data = []
            for i, article in enumerate(articles):
                progress = 40 + (i + 1) * (40 / len(articles))
                progress_bar.progress(int(progress))
                status_text.text(f"📝 Processing article {i + 1} of {len(articles)}...")
                summary_data = assistant.summarize_article(article)
                sentiment = assistant.analyze_sentiment(article['title'] + ' ' + article.get('summary', ''))
                article_data = {
                    **article,
                    **summary_data,
                    'sentiment': sentiment
                }
                articles_data.append(article_data)
                time.sleep(0.1)
            status_text.text("📋 Generating final digest...")
            progress_bar.progress(90)
            digest = assistant.generate_digest(topic, articles_data)
            progress_bar.progress(100)
            status_text.text("✅ Digest generated successfully!")
            st.markdown("---")
            st.markdown(
                f"""
                <div style='background: linear-gradient(90deg, #e3f2fd 0%, #fceabb 100%);padding:1.7rem 1.2rem 1.2rem 1.2rem;border-radius:16px;box-shadow:0 2px 12px #e3f2fd;'>
                    <h2 style='color:#1a73e8;font-size:2.1em;font-weight:800;margin-bottom:0.2em;'>📋 {digest['title']}</h2>
                    <p style='font-size:1.1em;'><b>🗓️ Date:</b> {digest['date']} &nbsp; | &nbsp; <b>🔎 Topic:</b> {digest['topic']} &nbsp; | &nbsp; <b>📰 Articles:</b> {digest['total_articles']}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
            sentiment_counts = digest['sentiment_summary']
            st.markdown(
                f"""
                <div style='margin-top:1.2rem;margin-bottom:1.2rem;'>
                    <span style='background:#e8f5e9;color:#388e3c;padding:0.7em 1.2em;border-radius:10px;margin-right:1em;font-weight:bold;font-size:1.1em;'>😊 Positive: {sentiment_counts['Positive']}</span>
                    <span style='background:#fffde7;color:#fbc02d;padding:0.7em 1.2em;border-radius:10px;margin-right:1em;font-weight:bold;font-size:1.1em;'>😐 Neutral: {sentiment_counts['Neutral']}</span>
                    <span style='background:#ffebee;color:#d32f2f;padding:0.7em 1.2em;border-radius:10px;font-weight:bold;font-size:1.1em;'>😞 Negative: {sentiment_counts['Negative']}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.markdown("<hr style='border:1px solid #e3f2fd;margin:1.5em 0;'>", unsafe_allow_html=True)
            st.markdown("### <span style='color:#1a73e8;'>🔑 Key Takeaways</span>", unsafe_allow_html=True)
            for i, article in enumerate(articles_data, 1):
                if article.get('core_insight'):
                    st.success(f"{article['core_insight']}  \n[Source: {article.get('source', 'Unknown')}]({article.get('url', '#')})", icon="✅")
            all_entities = []
            for article in articles_data:
                entities = article.get('named_entities', [])
                all_entities.extend(entities)
            unique_entities = list(dict.fromkeys(all_entities))
            if unique_entities:
                st.info(f"**Key Entities Mentioned:**  \n{' • '.join(unique_entities[:10])}")
            st.markdown("### <span style='color:#1a73e8;'>📊 Overall Analysis</span>", unsafe_allow_html=True)
            positive_count = sentiment_counts['Positive']
            negative_count = sentiment_counts['Negative']
            neutral_count = sentiment_counts['Neutral']
            if positive_count > negative_count:
                overall_tone = "**Positive**" if positive_count > neutral_count else "**Mixed (Positive-leaning)**"
            elif negative_count > positive_count:
                overall_tone = "**Negative**" if negative_count > neutral_count else "**Mixed (Negative-leaning)**"
            else:
                overall_tone = "**Neutral/Balanced**"
            st.markdown(f"The overall sentiment regarding <b>{digest['topic']}</b> is {overall_tone} based on <b>{digest['total_articles']}</b> analyzed articles. The coverage includes perspectives from <b>{len(set(article.get('source', 'Unknown') for article in articles_data))}</b> different news sources.", unsafe_allow_html=True)
            st.markdown("---")
            st.subheader("📄 Executive Summary Report")
            takeaways = []
            for i, article in enumerate(articles_data, 1):
                if article.get('core_insight'):
                    takeaways.append(f"• **Article {i}:** {article['core_insight']}")
            for takeaway in takeaways:
                st.markdown(takeaway)
            st.markdown("### 🔗 Source Links")
            for i, article in enumerate(articles_data, 1):
                source_name = article.get('source', 'Unknown Source')
                article_url = article.get('url', '#')
                article_title = article.get('title', 'Untitled')[:80] + "..."
                st.markdown(f"**{i}.** [{article_title}]({article_url}) - *{source_name}*")
            report_content = f"""# {digest['title']}
**Date:** {digest['date']}
**Topic:** {digest['topic']}
**Total Articles:** {digest['total_articles']}
**Sentiment Summary:** {sentiment_counts['Positive']} Positive, {sentiment_counts['Negative']} Negative, {sentiment_counts['Neutral']} Neutral

## Key Takeaways
"""
            for takeaway in takeaways:
                report_content += f"{takeaway}\n"
            report_content += "\n## Source Links\n"
            for i, article in enumerate(articles_data, 1):
                source_name = article.get('source', 'Unknown Source')
                article_url = article.get('url', '#')
                article_title = article.get('title', 'Untitled')
                report_content += f"{i}. {article_title} - {source_name}\n   Link: {article_url}\n\n"
            report_content += "\n## Detailed Article Analysis\n"
            for i, article in enumerate(articles_data, 1):
                report_content += f"\n### Article {i}: {article.get('title', 'Untitled')}\n"
                report_content += f"**Source:** {article.get('source', 'Unknown')}\n"
                report_content += f"**Sentiment:** {article.get('sentiment', 'Neutral')}\n"
                report_content += f"**Summary:** {article.get('summary', 'No summary available')}\n"
                if article.get('named_entities'):
                    entities = ', '.join(article['named_entities'][:5])
                    report_content += f"**Key Entities:** {entities}\n"
                if article.get('key_details'):
                    report_content += f"**Key Details:** {article['key_details']}\n"
                report_content += f"**URL:** {article.get('url', 'N/A')}\n"
                report_content += "---\n"
            st.subheader("📰 Detailed Article Summaries")
            for i, article in enumerate(articles_data, 1):
                with st.expander(f"Article {i}: {article['title'][:100]}..."):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(f"<span style='font-size:1.1em'><b>Source:</b> {article['source']}</span>", unsafe_allow_html=True)
                        st.markdown(f"<b>Published:</b> {article.get('published', 'Unknown')}", unsafe_allow_html=True)
                        if article.get('url'):
                            st.markdown(f"<b>Link:</b> <a href='{article['url']}' target='_blank'>Read Full Article</a>", unsafe_allow_html=True)
                    with col2:
                        sentiment_color = {
                            'Positive': '🟢',
                            'Negative': '🔴',
                            'Neutral': '🟡'
                        }
                        st.markdown(f"<b>Sentiment:</b> {sentiment_color.get(article['sentiment'], '🟡')} {article['sentiment']}", unsafe_allow_html=True)
                    st.markdown("<b>Summary:</b>", unsafe_allow_html=True)
                    st.markdown(f"{article.get('summary', 'Summary not available')}")
                    if article.get('named_entities'):
                        st.markdown("<b>Key Entities:</b>", unsafe_allow_html=True)
                        entities = ', '.join(article['named_entities'][:5])
                        st.markdown(f"_{entities}_")
                    if article.get('key_details'):
                        st.markdown("<b>Key Details:</b>", unsafe_allow_html=True)
                        st.markdown(article['key_details'])
            st.markdown("---")
            st.subheader("💾 Report Content")
            with st.expander("📄 Show Full Markdown Report"):
                st.code(report_content, language="markdown")
            with st.expander("📊 Show Digest Data (JSON)"):
                st.code(json.dumps(digest, indent=2, ensure_ascii=False), language="json")
            st.markdown("---")
        except Exception as e:
            logging.error(f"[Main] Error: {str(e)}")
            st.error(f"❌ An error occurred: {str(e)}")
        finally:
            progress_bar.empty()
            status_text.empty()

if __name__ == "__main__":
    main()