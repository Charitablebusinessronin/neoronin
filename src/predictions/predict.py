"""
BMAD Agent Memory - Prediction Engine
Generates predictions for pattern effectiveness, learning velocity, and knowledge transfer.
"""

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

try:
    import joblib
    import pandas as pd
    from neo4j import AsyncGraphDatabase
except ImportError:
    print("Warning: Prediction dependencies not installed. Run: pip install -r requirements.txt")
    joblib = None
    pd = None
    AsyncGraphDatabase = None


class PredictionEngine:
    """Main prediction orchestrator for all BMAD prediction models."""
    
    def __init__(self, neo4j_uri: str = None, neo4j_password: str = None):
        """Initialize prediction engine with Neo4j connection.
        
        Args:
            neo4j_uri: Neo4j connection URI (default: from env NEO4J_URI)
            neo4j_password: Neo4j password (default: from env NEO4J_PASSWORD)
        """
        self.neo4j_uri = neo4j_uri or os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.neo4j_password = neo4j_password or os.getenv("NEO4J_PASSWORD")
        
        if AsyncGraphDatabase:
            self.driver = AsyncGraphDatabase.driver(
                self.neo4j_uri, 
                auth=("neo4j", self.neo4j_password)
            )
        else:
            self.driver = None
            print("Warning: Neo4j driver not available")
        
        self.models_dir = Path("_bmad-output/predictions/models")
        self.output_dir = Path("_bmad-output/predictions/forecasts/daily")
        self.models = {}
        
        # Load models if available
        if joblib and self.models_dir.exists():
            self._load_models()
    
    def _load_models(self) -> None:
        """Load all trained prediction models."""
        model_files = {
            "pattern_effectiveness": "pattern_success_predictor.pkl",
            "confidence_score": "confidence_score_rf.pkl",
            "promotion_ranking": "promotion_ranking_svm.pkl",
        }
        
        for model_name, filename in model_files.items():
            model_path = self.models_dir / filename
            if model_path.exists():
                try:
                    self.models[model_name] = joblib.load(model_path)
                    print(f"✓ Loaded model: {model_name}")
                except Exception as e:
                    print(f"⚠ Failed to load {model_name}: {e}")
    
    async def predict_pattern_effectiveness(
        self, 
        pattern_ids: List[str], 
        group_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Predict success probability for specified patterns.
        
        Args:
            pattern_ids: List of pattern node IDs to predict
            group_id: Optional project scope (faith-meats, diff-driven-saas, global-coding-skills)
        
        Returns:
            Dict with predictions, metadata, and confidence scores
        """
        if not self.driver:
            return {"error": "Neo4j driver not initialized"}
        
        if "pattern_effectiveness" not in self.models:
            return {"error": "Pattern effectiveness model not loaded"}
        
        run_id = f"pred_{datetime.now().strftime('%Y%m%d_%H%M')}"
        start_time = datetime.now()
        
        # Extract features from Neo4j
        features_df = await self._extract_pattern_features(pattern_ids, group_id)
        
        if features_df.empty:
            return {
                "run_id": run_id,
                "error": "No features extracted",
                "pattern_ids": pattern_ids
            }
        
        # Generate predictions
        model = self.models["pattern_effectiveness"]
        
        try:
            # Predict success probability
            predictions = model.predict_proba(features_df)[:, 1]
            confidence_scores = model.predict_proba(features_df).max(axis=1)
            
            # Format output
            results = []
            for i, pattern_id in enumerate(pattern_ids):
                if i < len(predictions):
                    results.append({
                        "entity_id": pattern_id,
                        "entity_type": "Pattern",
                        "prediction_value": float(predictions[i]),
                        "confidence": float(confidence_scores[i]),
                        "explanation": {
                            "top_features": self._get_feature_importance(
                                model, features_df.iloc[i]
                            )
                        }
                    })
            
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
            
            output = {
                "run_id": run_id,
                "model_name": "pattern_effectiveness",
                "model_version": "v1.0.0",
                "timestamp": datetime.now().isoformat(),
                "predictions": results,
                "metadata": {
                    "prediction_count": len(results),
                    "processing_time_ms": processing_time,
                    "group_id": group_id
                }
            }
            
            # Save predictions
            self._save_predictions(output)
            
            return output
            
        except Exception as e:
            return {
                "run_id": run_id,
                "error": f"Prediction failed: {str(e)}",
                "pattern_ids": pattern_ids
            }
    
    async def _extract_pattern_features(
        self, 
        pattern_ids: List[str], 
        group_id: Optional[str]
    ) -> 'pd.DataFrame':
        """
        Extract features from Neo4j for pattern prediction.
        
        Args:
            pattern_ids: Pattern IDs to extract features for
            group_id: Optional project scope filter
        
        Returns:
            DataFrame with extracted features
        """
        if not pd:
            return pd.DataFrame() if pd else None
        
        query = """
        MATCH (p:Pattern)
        WHERE p.id IN $pattern_ids
        OPTIONAL MATCH (p)<-[:USED_PATTERN]-(s:Solution)
        OPTIONAL MATCH (s)-[:LED_TO]->(o:Outcome)
        WITH p, 
             count(DISTINCT s) AS usage_count,
             avg(CASE WHEN o.success = true THEN 1.0 ELSE 0.0 END) AS success_rate,
             count(DISTINCT o.agent_id) AS agent_diversity
        RETURN p.id AS pattern_id,
               coalesce(usage_count, 0) AS usage_count_30d,
               coalesce(success_rate, 0.0) AS success_rate_30d,
               coalesce(agent_diversity, 0) AS agent_diversity,
               0.85 AS domain_similarity_score
        """
        
        try:
            async with self.driver.session() as session:
                result = await session.run(query, pattern_ids=pattern_ids)
                records = [dict(record) async for record in result]
                
                if records:
                    return pd.DataFrame(records)
                else:
                    return pd.DataFrame()
        except Exception as e:
            print(f"Feature extraction error: {e}")
            return pd.DataFrame()
    
    def _get_feature_importance(
        self, 
        model: Any, 
        feature_row: 'pd.Series'
    ) -> List[Dict]:
        """Extract top 3 feature importances.
        
        Args:
            model: Trained ML model
            feature_row: Single row of features
        
        Returns:
            List of top 3 features with importance scores
        """
        if not hasattr(model, 'feature_importances_'):
            return []
        
        try:
            importances = model.feature_importances_
            top_indices = importances.argsort()[-3:][::-1]
            
            return [
                {
                    "feature_name": str(feature_row.index[i]),
                    "importance": float(importances[i])
                }
                for i in top_indices
                if i < len(feature_row.index)
            ]
        except Exception:
            return []
    
    def _save_predictions(self, output: Dict[str, Any]) -> None:
        """Save predictions to JSON file.
        
        Args:
            output: Prediction output dictionary
        """
        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.fromisoformat(output["timestamp"])
            date_str = timestamp.strftime("%Y-%m-%d")
            filepath = self.output_dir / f"{date_str}_predictions.json"
            
            with open(filepath, "w") as f:
                json.dump(output, f, indent=2, default=str)
            
            print(f"✓ Saved predictions to: {filepath}")
        except Exception as e:
            print(f"⚠ Failed to save predictions: {e}")
    
    async def close(self) -> None:
        """Close Neo4j connection."""
        if self.driver:
            await self.driver.close()


# CLI Entry Point
async def main():
    """Generate daily predictions for all patterns."""
    engine = PredictionEngine()
    
    if not engine.driver:
        print("Error: Could not connect to Neo4j. Set NEO4J_URI and NEO4J_PASSWORD.")
        return
    
    # Get all active patterns from Neo4j
    try:
        async with engine.driver.session() as session:
            result = await session.run("MATCH (p:Pattern) RETURN p.id AS pattern_id LIMIT 10")
            pattern_ids = [record["pattern_id"] async for record in result]
        
        if not pattern_ids:
            print("No patterns found in database.")
            await engine.close()
            return
        
        print(f"\n🔮 Generating predictions for {len(pattern_ids)} patterns...\n")
        
        # Generate predictions
        predictions = await engine.predict_pattern_effectiveness(pattern_ids)
        
        if "error" in predictions:
            print(f"❌ Error: {predictions['error']}")
        else:
            print(f"✅ Generated {predictions['metadata']['prediction_count']} predictions")
            print(f"⏱️  Processing time: {predictions['metadata']['processing_time_ms']}ms")
            print(f"📊 Run ID: {predictions['run_id']}")
        
    except Exception as e:
        print(f"❌ Prediction failed: {e}")
    finally:
        await engine.close()


if __name__ == "__main__":
    asyncio.run(main())
