from app.routing import classify_intent


def test_consumer_and_company_complaint_intents_are_separate():
    consumer = classify_intent("我想向 CFPB 提交消费投诉，官方流程是什么？")
    company = classify_intent("How does a company receive and respond to a CFPB complaint?")
    assert consumer.intent == "consumer_submit_complaint"
    assert company.intent == "company_respond_complaint"
    assert consumer.source_url_families != company.source_url_families
    assert classify_intent("What happens after a consumer submits a complaint to the CFPB?").intent == "consumer_submit_complaint"


def test_unauthorized_transaction_routes_to_official_sources():
    route = classify_intent("I do not recognize a credit card transaction")
    assert route.intent == "unauthorized_transaction"
    assert any("unauthorized-use" in url for url in route.source_url_families)


def test_exact_term_variants_route_to_specific_families():
    assert classify_intent("Which official sources cover an unrecognized card purchase?").intent == "unauthorized_transaction"
    assert classify_intent("I see an unfamiliar credit card charge and need support.").intent == "unauthorized_transaction"
    assert classify_intent("Which official guidance covers a duplicate charge on a credit card bill?").intent == "billing_error"
    regulation = classify_intent("客服回答账单争议时，法规证据应该和普通 CFPB 指导如何区分？")
    assert regulation.intent == "regulation_lookup"
    assert regulation.source_url_families == ("https://www.consumerfinance.gov/rules-policy/regulations/1026/13/",)


def test_unknown_question_does_not_apply_a_specific_source_filter():
    route = classify_intent("What is the weather tomorrow?")
    assert route.intent == "general_support"
    assert route.source_url_families == ()


def test_consumer_process_variants_do_not_route_to_company_page():
    questions = [
        "消费者提交 CFPB 投诉后，通常会经历哪些公开流程步骤？",
        "如何找到 CFPB 官方投诉提交入口，而不是企业处理页面？",
        "Where is the official CFPB process for submitting a consumer complaint?",
        "How can a consumer distinguish the CFPB submission flow from a company's response flow?",
    ]
    for question in questions:
        route = classify_intent(question)
        assert route.intent == "consumer_submit_complaint"
        assert route.audience == "consumer"
        assert route.source_url_families == ("https://www.consumerfinance.gov/complaint/process/",)
