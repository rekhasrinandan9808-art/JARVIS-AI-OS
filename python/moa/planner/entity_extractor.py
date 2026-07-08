import re


class EntityExtractor:

    def extract(self, intent: str, command: str):

        if intent == "search":

            query = re.sub(
                r"^(search|search for|find|find me|look up|lookup|google|browse|web search)\s+",
                "",
                command,
                flags=re.IGNORECASE,
            )

            return {
                "query": query.strip()
            }

        elif intent == "research":

            topic = re.sub(
                r"^(research|study|learn|tell me about|explain)\s+",
                "",
                command,
                flags=re.IGNORECASE,
            )

            return {
                "topic": topic.strip()
            }

        elif intent == "syntax":

            code = re.sub(
                r"^(syntax|check syntax)\s+",
                "",
                command,
                flags=re.IGNORECASE,
            )

            return {
                "code": code
            }

        elif intent == "translate":

            text = re.sub(
                r"^translate\s+",
                "",
                command,
                flags=re.IGNORECASE,
            )

            return {
                "text": text
            }

        elif intent == "weather":

            city = command.replace("weather", "").replace("forecast", "").strip()

            return {
                "city": city
            }

        return {}