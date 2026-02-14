import pandas as pd
import json
import random
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.decomposition import TruncatedSVD
from collections import Counter

class GiftRecommender:
    def __init__(self, products):
        self.products = products
        self.df = pd.DataFrame(products)
        
        print("Loading BERT model...")
        self.bert_model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # --- Use Title and Tags for recommendations ---
        self.df["combined_text"] = (
            self.df["title"].fillna("") + " " + 
            self.df["description"].fillna("") + " " + 
            self.df["tags"].apply(lambda x: " ".join(x) if isinstance(x, list) else str(x))
        )
        
        # Pre-compute embeddings for semantic search
        self.product_embeddings = self.bert_model.encode(self.df["combined_text"].tolist())
        print("Product Embeddings generated using Title and Tags.")
        
    def get_content_based(self, query, top_k=8):
        # Encode the User's Query into the same Vector Space
        query_embedding = self.bert_model.encode([query])
        # Calculate Cosine Similarity
        similarities = cosine_similarity(query_embedding, self.product_embeddings).flatten()
        # Get Top-K Indices
        top_indices = similarities.argsort()[-top_k:][::-1]
        results = []
        for idx in top_indices:
            product = self.products[idx].copy()
            product['confidence'] = round(float(similarities[idx]) * 100, 1)
            product['model_used'] = "Content based"
            results.append(product)
        return results

    def get_collaborative_based(self, interactions, top_k=8):
        """
        Algo: Matrix Factorization (SVD).
        Finds latent patterns in user behavior (e.g., "Users who bought X also bought Y").
        """
        if not interactions or len(interactions) < 5:
            return self.get_random_recommendations(top_k, "Collaborative (Cold Start)")

        # 1. Build Interaction Matrix (Rows=Users, Cols=Products)
        product_ids = sorted(list(set(i.product_id for i in interactions)))
        user_ids = sorted(list(set(i.user_id for i in interactions)))
        
        # Map IDs to Matrix Indices
        prod_map = {pid: i for i, pid in enumerate(product_ids)}
        user_map = {uid: i for i, uid in enumerate(user_ids)}
        
        # Create Matrix
        matrix = np.zeros((len(user_ids), len(product_ids)))
        for i in interactions:
            if i.product_id in prod_map and i.user_id in user_map:
                # Score: Purchase=5, Like=3, Dislike=-1
                score = 5 if i.action_type == 'purchase' else (3 if i.action_type == 'like' else 1)
                matrix[user_map[i.user_id]][prod_map[i.product_id]] = score

        # 2. Apply SVD (Singular Value Decomposition)
        # Reduces noise and fills in "blank spots" with predictions
        try:
            n_components = min(10, len(product_ids)-1) # Ensure valid dimensions
            svd = TruncatedSVD(n_components=n_components, random_state=42)
            matrix_reduced = svd.fit_transform(matrix)
            matrix_reconstructed = svd.inverse_transform(matrix_reduced)
            
            # Sum up predicted scores for all products (Global Trend). In a real user session, we would look at a specific user's row.
            # Here, we show globally trending items based on latent features.
            avg_scores = matrix_reconstructed.mean(axis=0)
            
            # Get Top Indices
            top_indices = avg_scores.argsort()[-top_k:][::-1]
            
            results = []
            for idx in top_indices:
                real_pid = product_ids[idx]
                # Match the ID as a string to the database ID
                prod = next((p for p in self.products if str(p['id']) == real_pid), None)
                if prod:
                    p_copy = prod.copy()
                    # Ensure the rating from the CSV is included in the dictionary
                    p_copy['rating'] = prod.get('rating', 0.0) 
                    p_copy['confidence'] = round(float(avg_scores[idx]) * 10 + 50, 1)
                    p_copy['model_used'] = "SVD Matrix Factorization"
                    results.append(p_copy)
            return results
            
        except Exception as e:
            print(f"SVD Error (Falling back to popularity): {e}")
            return self.get_random_recommendations(top_k, "Fallback Popularity")

    def update_rl_weights(self, current_weights_json, action, product_price):
        """
        RL Algo : The Reinforcement Learning (RL) Feedback Loop.
        Adjusts weights dynamically based on user actions.
        """
        # Parse JSON if needed
        if isinstance(current_weights_json, str):
            weights = json.loads(current_weights_json)
        else:
            weights = current_weights_json.copy()

        # Learning Rate (How fast the AI adapts)
        alpha = 0.05 

        # Logic:
        # If 'like'/'purchase': Trust relevance more, trust price point.
        # If 'dislike': Increase novelty (show different things), reduce relevance trust.
        
        if action in ['like', 'purchase']:
            weights['relevance_weight'] = min(1.0, weights['relevance_weight'] + alpha)
            weights['novelty_weight'] = max(0.0, weights['novelty_weight'] - alpha)
            # If they buy expensive, increase tolerance for price
            if product_price > 1000:
                weights['price_weight'] = max(0.1, weights['price_weight'] - alpha) 
        
        elif action == 'dislike':
            weights['relevance_weight'] = max(0.1, weights['relevance_weight'] - alpha)
            weights['novelty_weight'] = min(0.5, weights['novelty_weight'] + alpha)
        
        return json.dumps(weights)

    def get_hybrid_based(self, query, occasion=None, relationship=None, top_k=20):
        	
        query_embedding = self.bert_model.encode([query])
        bert_scores = cosine_similarity( query_embedding, self.product_embeddings).flatten()
	
		# Get top 50 semantic candidates
        candidate_indices = bert_scores.argsort()[-50:][::-1]
	
        results = []
	
        for idx in candidate_indices:
            score = float(bert_scores[idx])
            prod = self.products[idx]
            text_context = (prod["title"] + " " + " ".join(prod["tags"])).lower()
	
            occasion_match = 1 if occasion and occasion.lower() in text_context else 0
            relationship_match = 1 if relationship and relationship.lower() in text_context else 0
	
			# Proper weighted fusion
            final_score = ( 0.75 * score + 0.15 * occasion_match + 0.10 * relationship_match )
	
            results.append({**prod, "confidence": round(final_score * 100, 1), "model_used": "Hybrid (Semantic + Metadata)"
				}
			)
        return sorted(results, key=lambda x: x["confidence"], reverse=True)[:top_k]

    def update_model_with_interactions(self, interactions):
        # Stub for compatibility (SVD calculates on the fly, so no training loop needed here)
        pass

    def get_random_recommendations(self, k, model_name):
        selected = random.sample(self.products, min(k, len(self.products)))
        results = []
        for p in selected:
            p_copy = p.copy()
            p_copy['confidence'] = 50.0
            p_copy['model_used'] = model_name
            results.append(p_copy)
        return results