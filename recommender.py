import nltk
import pandas as pd
import numpy as np
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from nltk.sentiment import SentimentIntensityAnalyzer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.linear_model import LogisticRegression
from collections import Counter


nltk.download("punkt", quiet=True)
nltk.download("stopwords", quiet=True)
nltk.download("wordnet", quiet=True)
nltk.download("vader_lexicon", quiet=True)

class GiftRecommender:
    def __init__(self, products):
        self.products = products
        self.df = pd.DataFrame(products)
    
        self.stop_words = set(stopwords.words("english"))
        self.lemmatizer = WordNetLemmatizer()
        self.sentiment = SentimentIntensityAnalyzer()
        self.df["combined_text"] = (
            self.df["title"].fillna("") + " " + 
            self.df["description"].fillna("") + " " + 
            self.df["tags"].apply(lambda x: " ".join(x) if isinstance(x, list) else str(x))
        )
        self.df["clean_text"] = self.df["combined_text"].apply(self.preprocess_text)

        self.vectorizer = TfidfVectorizer(max_features=5000, stop_words='english')
        self.tfidf_matrix = self.vectorizer.fit_transform(self.df["clean_text"])

        median_price = self.df["price"].median()
        self.df["target_label"] = (self.df["price"] > median_price).astype(int)
        
        if self.df["target_label"].nunique() < 2:
            self.df.loc[0, "target_label"] = 1 - self.df.loc[0, "target_label"]

        self.lr_model = LogisticRegression()
        self.lr_model.fit(self.tfidf_matrix, self.df["target_label"])

    def preprocess_text(self, text):
        tokens = nltk.word_tokenize(str(text).lower())
        tokens = [self.lemmatizer.lemmatize(t) for t in tokens if t.isalnum()]
        return " ".join(tokens)

    def get_content_based(self, query, top_k=8):
        clean_query = self.preprocess_text(query)
        query_vec = self.vectorizer.transform([clean_query])
        
        cosine_sim = cosine_similarity(query_vec, self.tfidf_matrix).flatten()
        
        top_indices = cosine_sim.argsort()[-top_k:][::-1]
        
        results = []
        for idx in top_indices:
            product = self.products[idx].copy()
            product['confidence'] = round(float(cosine_sim[idx]) * 100, 1)
            product['model_used'] = "Content-Based (TF-IDF)"
            results.append(product)
        return results


    def get_collaborative_based(self, interactions, top_k=8):

        if not interactions:
            # COLD START: Return random items if no one has interacted yet
            return self.get_random_recommendations(top_k, "Collaborative (Cold Start)")
        product_counts = Counter([i.product_id for i in interactions])
        most_common_ids = [int(pid) for pid, count in product_counts.most_common(top_k)]
        
        results = []
        for pid in most_common_ids:
            prod = next((p for p in self.products if p['id'] == pid), None)
            if prod:
                p_copy = prod.copy()
                p_copy['confidence'] = 95.0  # High confidence for popular items
                p_copy['model_used'] = "Collaborative (Popularity)"
                results.append(p_copy)

        if len(results) < top_k:
            needed = top_k - len(results)
            results.extend(self.get_random_recommendations(needed, "Collaborative (Filler)"))
        return results

    def update_model_with_interactions(self, interactions):
        """Retrains the LR model based on purchase data instead of price."""
        if not interactions:
            return
    
        # 1. Identify which products were actually purchased
        # Filter interactions for 'purchase' actions [cite: 22, 31]
        purchase_ids = [int(i.product_id) for i in interactions if i.action_type == 'purchase']
    
        if not purchase_ids:
            return

        # 2. Create labels: 1 for purchased items, 0 for others
        new_labels = [1 if p['id'] in purchase_ids else 0 for p in self.products]
    
        # 3. Retrain if we have at least one example of both classes
        if len(set(new_labels)) > 1:
            self.lr_model.fit(self.tfidf_matrix, new_labels)
        
            
    def get_hybrid_based(self, query, occasion=None, relationship=None, top_k=20):
        # 1. Hard Filter: Prioritize the occasion if provided [cite: 282-283]
        filtered_df = self.df
        if occasion and occasion.strip():
            mask = self.df['combined_text'].str.contains(occasion, case=False, na=False)
            filtered_df = self.df[mask]
    
        if filtered_df.empty:
            filtered_df = self.df

        # 2. Vectorize the search query [cite: 275]
        clean_query = self.preprocess_text(query)
        query_vec = self.vectorizer.transform([clean_query])
    
        subset_indices = filtered_df.index
        subset_tfidf = self.tfidf_matrix[subset_indices]

        # 3. Calculate scores
        cosine_sims = cosine_similarity(query_vec, subset_tfidf).flatten() 
        lr_probs = self.lr_model.predict_proba(subset_tfidf)[:, 1]

        results = []
        for i, idx in enumerate(subset_indices):
            # Base AI Score (70% Relevance, 30% Preference) [cite: 284]
            base_score = (0.7 * cosine_sims[i]) + (0.3 * lr_probs[i])
        
            # 4. INTENT BOOSTING: Specifically look for the relationship 
            boost = 0
            product_text = self.df.loc[idx, 'combined_text'].lower()
        
            # We search specifically for the relationship in the product text
            if relationship and relationship.lower() in product_text:
                boost += 0.25  
            
            if occasion and occasion.lower() in product_text:
                boost += 0.40  
            if occasion and "wedding" in occasion.lower() and "birthday" in product_text:
                boost -= 0.30

            final_score = max(0.0, min(base_score + boost, 1.0))
        
            product = self.products[idx].copy()
            product['confidence'] = round(float(final_score) * 100, 1)
            product['model_used'] = "Context-Prioritized Hybrid"
            results.append(product)

        # Sort results to put the highest confidence at the top
        results = sorted(results, key=lambda x: x['confidence'], reverse=True)
        return results[:top_k]

    def get_random_recommendations(self, k, model_name):
        import random
        selected = random.sample(self.products, min(k, len(self.products)))
        results = []
        for p in selected:
            p_copy = p.copy()
            p_copy['confidence'] = 50.0
            p_copy['model_used'] = model_name
            results.append(p_copy)
        return results