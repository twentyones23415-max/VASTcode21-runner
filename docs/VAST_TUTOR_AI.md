# VAST Tutor AI — Product Architecture

## Purpose
VAST Tutor AI is a paid educational product line for structured MT5 learning, chart understanding, screenshot-based review and prediction-to-outcome learning. It must not be presented as a guaranteed signal service, account-management service or profit promise.

## Product family
- **VAST Tutor AI** — 24/7 educational tutor, lessons, quizzes, progress tracking and guided review.
- **VAST Vision AI** — screenshot/chart analysis module that extracts visible chart context and combines it with verified current market context when available.
- **VAST Outcome Lab** — stores a time-stamped scenario, then later compares what happened versus the original scenario to create a learning review.

## Planned launch pricing
- **Tutor Core — €19/month**: tutor access, lessons/quizzes, learning progress, 15 screenshot analyses/month.
- **Vision Pro — €39/month**: 60 screenshot analyses/month, XAUUSD/BTCUSD context, scenario/invalidation review and prediction-to-outcome journal.
- **VAST Lab — €69/month**: 180 screenshot analyses/month, deeper review mode, longer scenario history and priority beta features.

These are planned launch prices and can be adjusted before paid checkout is enabled based on infrastructure cost and beta usage.

## Screenshot analysis pipeline
1. User uploads a chart screenshot.
2. Secure image validation strips unsupported files and enforces size limits.
3. Vision layer extracts only visible evidence: symbol/timeframe when shown, candle structure, visible price levels, trend/range structure, annotations and visible indicator state.
4. Market-context layer fetches verified current XAUUSD/BTCUSD data when available.
5. News-context layer checks the VASTcode21 Market Intelligence feed for current macro, gold and bitcoin risk context.
6. Scenario engine returns multiple scenarios rather than a single deterministic instruction.
7. Tutor layer explains evidence, uncertainty, invalidation conditions and a lesson tailored to the user's level.
8. Outcome Lab stores the time-stamped scenario and later performs a prediction-to-outcome review.

## Output contract
A Vision analysis should contain:
- Detected symbol/timeframe, or `unknown` when not visible.
- Visible structure summary.
- Bullish / bearish / neutral scenario set.
- Evidence supporting each scenario.
- Invalidation conditions.
- Current news/event risk when verified.
- Limits and uncertainty statement.
- Educational takeaway.
- No direct account-specific position sizing unless the user explicitly supplies inputs and the output remains educational.

## Safety and trust requirements
- Never claim guaranteed accuracy or guaranteed returns.
- Never fabricate live prices, live news or a timeframe that is not visible/verified.
- Clearly distinguish screenshot evidence from live external context.
- Do not execute trades or manage accounts.
- Do not store screenshots until consent, retention policy and secure storage are implemented.
- The public upload prototype must remain local-only until a backend with privacy controls is connected.
- Billing must not be enabled before the product can actually deliver the paid features.

## Backend requirements
- Authenticated user accounts.
- Server-side AI/vision processing with secret credentials never exposed to browser code.
- Usage metering per plan and monthly analysis-credit reset.
- Secure upload handling with short retention by default.
- Persistent learning progress and Outcome Lab records.
- Verified market-data source for any claim marked real-time/live.
- Payment provider for subscriptions and webhooks.
- Error logging, abuse protection, rate limits and cost caps.

## Evolution loop
The product should evolve through small verified increments:
1. Improve public product UX and documentation.
2. Build backend/API contract and tests.
3. Connect secure user accounts.
4. Connect AI/vision backend.
5. Connect verified market data.
6. Implement Outcome Lab.
7. Connect billing only after the core experience is functional.
8. Run private beta, measure failures/cost/retention and adjust limits/pricing.
9. Expand lessons and automated evaluations based on observed user needs.

## Success metrics
Track educational and product-quality metrics rather than trading P&L claims: lesson completion, quiz improvement, screenshot-analysis usefulness rating, repeat usage, prediction-review completion, false/live-context error rate, support load, infrastructure cost per active user and subscription retention.
