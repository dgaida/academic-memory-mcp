from mcp_university.summarizer.engine import Summarizer

def test_answer_question(mock_llm_client_wrapper):
    summarizer = Summarizer()
    mock_llm_client_wrapper.chat.return_value = {
        'message': {'content': 'Die Antwort ist 42.'}
    }
    answer = summarizer.answer_question("Was?", "Kontext")
    assert answer == "Die Antwort ist 42."

def test_summarize_email(mock_llm_client_wrapper):
    summarizer = Summarizer()
    mock_llm_client_wrapper.chat.return_value = {
        'message': {'content': '# E-Mail Zusammenfassung'}
    }
    summary = summarizer.summarize_file("test.msg", "content")
    assert "# E-Mail Zusammenfassung" in summary

def test_summarize_long_doc(mock_llm_client_wrapper):
    summarizer = Summarizer()
    mock_llm_client_wrapper.chat.side_effect = [
        {'message': {'content': 'Typ'}},
        {'message': {'content': 'Zusammenfassung'}}
    ]
    summary = summarizer.summarize_file("test.pdf", "content")
    assert "Zusammenfassung" in summary

def test_answer_question_error(mock_llm_client_wrapper):
    summarizer = Summarizer()
    mock_llm_client_wrapper.chat.side_effect = Exception("error")
    answer = summarizer.answer_question("query", "context")
    assert answer is None
