import json
import re
import httpx
from app.config import get_settings


class AIClient:
    def __init__(self) -> None:
        self.settings = get_settings()

    def analyze_impact(self, payload: dict) -> dict:
        if not self.settings.ai_api_key.get_secret_value() or not self.settings.ai_base_url:
            return self._fallback_analysis(payload)

        headers = {
            "Authorization": f"Bearer {self.settings.ai_api_key.get_secret_value()}",
            "Content-Type": "application/json",
        }
        body = {
            "model": self.settings.ai_model,
            "messages": [
                {"role": "system", "content": IMPACT_SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ],
            "temperature": self.settings.ai_temperature,
        }
        base_url = self.settings.ai_base_url.rstrip("/")
        if not base_url.endswith("/chat/completions"):
            base_url += "/chat/completions"
        ai_timeout = self.settings.ai_timeout_seconds
        with httpx.Client(timeout=ai_timeout) as client:
            resp = client.post(base_url, headers=headers, json=body)
            resp.raise_for_status()
        data = resp.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        if not content or not content.strip():
            raise ValueError("AI returned empty content")
        # Strip thinking/reasoning tags (common with qwen models)
        content = re.sub(r"<think>[\s\S]*?</think>", "", content).strip()
        # Extract JSON from markdown code blocks if present
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", content)
        if json_match:
            content = json_match.group(1).strip()
        # If still not starting with '{', try to find first JSON object
        if not content.startswith("{"):
            brace_match = re.search(r"\{[\s\S]*\}", content)
            if brace_match:
                content = brace_match.group(0)
        return json.loads(content)

    def _fallback_analysis(self, payload: dict) -> dict:
        symbol = payload.get("us_symbol", "")
        pct_change = float(payload.get("pct_change") or 0)
        direction = "利多" if pct_change > 0 else "利空" if pct_change < 0 else "中性"
        strength = 3 if abs(pct_change) >= 3 else 2
        return {
            "report_date": payload.get("report_date"),
            "us_trade_date": payload.get("trade_date"),
            "us_symbol": symbol,
            "us_name": payload.get("us_name"),
            "turnover_rank": payload.get("turnover_rank"),
            "pct_change": pct_change,
            "amount": payload.get("amount"),
            "reason_category": "AI分析",
            "event_summary": "基于行情异动生成初步判断",
            "mapped_cn_targets": [],
            "impact_direction": direction,
            "impact_strength": strength,
            "impact_score": min(1.0, max(0.1, abs(pct_change) / 10)),
            "confidence": 0.3,
            "event_source": "AI分析",
            "source_type": "ai_analysis",
            "ai_model": self.settings.ai_model,
        }


IMPACT_SYSTEM_PROMPT = """
你是美股隔夜事件映射 A 股的投研分析助手。只输出 JSON，不输出解释。
必须包含字段：report_date, us_trade_date, us_symbol, us_name, turnover_rank, pct_change, amount,
reason_category, event_summary, mapped_cn_targets, impact_direction, impact_strength,
impact_score, confidence, event_source, source_type, ai_model。
规则：
1. reason_category 不超过 10 个中文字符。
2. event_summary 不超过 30 个中文字符。
3. impact_direction 只能是：利多、利空、偏多、偏空、中性。
4. impact_strength 只能是 1-5 的整数。
5. event_source 只能选择用户输入 event_candidates 中的 URL；没有可靠 URL 时写 AI分析。
6. 严禁编造 URL、公司公告、新闻事实。
7. mapped_cn_targets 最多 5 个，每个包含 symbol, name, relation_type, theme。
"""
