from typing import List, Dict, Any

class PromptContextBuilder:
    @staticmethod
    def build_context(hits: List[Dict[str, Any]]) -> str:
        """
        Builds a structured, numbered context string with source file, page, 
        and section headers to pass into the LLM prompt.
        """
        if not hits:
            return "No relevant context found."

        context_parts = []
        for idx, hit in enumerate(hits, start=1):
            metadata = hit.get("metadata", {})
            source_file = metadata.get("source_file", "unknown")
            product_name = metadata.get("product_name")
            if not product_name:
                product_name = source_file
                for ext in [".pdf", ".docx", ".txt", "_parsed.json"]:
                    product_name = product_name.replace(ext, "")
                pn_lower = product_name.lower()
                for prefix in ["dummy_", "dumy_", "dummy-", "dumy-", "dummy ", "dumy "]:
                    if pn_lower.startswith(prefix):
                        product_name = product_name[len(prefix):]
                        pn_lower = pn_lower[len(prefix):]
                if pn_lower.startswith("dummy") or pn_lower.startswith("dumy"):
                    product_name = product_name[5:]
                product_name = product_name.replace("-", " ").replace("_", " ")
                product_name = product_name.strip()
                
            section = metadata.get("section", "General")
            page = metadata.get("page", 1)
            # Use 'content' for the new dictionary schema instead of 'text'
            text = hit.get("content", "")

            # Formulate citation header with Product name followed by content block
            part = (
                f"[{idx}] Source: {source_file} | Product: {product_name} | Section: {section} | Page: {page}\n"
                f"Content:\n{text.strip()}"
            )
            context_parts.append(part)

        # Separate each context block with double newlines
        return "\n\n".join(context_parts)
