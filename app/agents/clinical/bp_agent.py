"""
Blood Pressure Agent — RAG-powered (clinical)
Answers hypertension questions using the 'blood_pressure_knowledge' Qdrant collection.
Uses patient's medical_description and last_test_results for personalized responses.
"""
import google.generativeai as genai
from app.core.config import get_settings
from app.db.qdrant_client import get_qdrant
from app.core.prompts import CLINICAL_AGENT_PROMPT, _language_instruction

settings = get_settings()
genai.configure(api_key=settings.gemini_api_key)


class BloodPressureAgent:
    name = "blood_pressure_agent"
    collection = "blood_pressure_knowledge"
    display_name = "Blood Pressure"
    specialty = "Blood Pressure"

    async def _retrieve_context(self, query: str, top_k: int = 5) -> list[str]:
        """Embed query and retrieve relevant chunks from the blood pressure Qdrant collection."""
        result = genai.embed_content(
            model="models/gemini-embedding-001",
            content=query,
            task_type="retrieval_query",
        )
        query_vector = result["embedding"]
        client = get_qdrant()
        result = client.query_points(
            collection_name=self.collection,
            query=query_vector,
            limit=top_k,
        )
        return [hit.payload.get("text", "") for hit in result.points]

    async def answer(self, question: str, patient_context: dict, language: str = "ar") -> str:
        chunks = await self._retrieve_context(question)
        context_text = "\n\n".join(chunks)

        name         = patient_context.get("full_name", "Patient")
        diseases     = ", ".join(patient_context.get("diseases", []))
        medical_desc = patient_context.get("medical_description") or "Not available"
        test_results = patient_context.get("last_test_results") or "No lab results on record"

        prompt = CLINICAL_AGENT_PROMPT.format(
            specialty=self.specialty,
            language_instruction=_language_instruction(language),
            name=name,
            diseases=diseases,
            medical_desc=medical_desc,
            test_results=test_results,
            context_text=context_text,
            question=question,
        )
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(prompt)
        return response.text
