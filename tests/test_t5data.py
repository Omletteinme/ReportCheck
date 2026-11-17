from src.t5data import align, normalize, sentence_pairs, split_by_id

SOURCE = "FINDINGS: The cardiac and mediastinal silhouettes are unremarkable. There is no pleural effusion or pneumothorax."
LAY = "The heart and the area around it look normal. There is no fluid around the lungs or air leak."


def test_normalize_ignores_labels_case_and_punctuation():
    assert normalize("FINDINGS: Heart size is normal.  IMPRESSION: No acute disease.") == "heart size is normal no acute disease"
    assert normalize("Heart size, normal!") == normalize("heart size normal")


def test_align_pairs_sentences_in_order_when_the_counts_match():
    pairs = align(SOURCE, LAY)
    assert pairs == [("The cardiac and mediastinal silhouettes are unremarkable.", "The heart and the area around it look normal."),
                     ("There is no pleural effusion or pneumothorax.", "There is no fluid around the lungs or air leak.")]


def test_align_gives_nothing_when_the_counts_differ():
    assert align(SOURCE, LAY + " Nothing else is seen.") == []


def test_sentence_pairs_keep_only_rewritable_sentences_with_a_safe_simpler_rewrite():
    source = ("There is no pleural effusion or pneumothorax. The XXXX is unremarkable today. No pneumothorax. "
              "There is a 6 mm nodule in the right lung. The lungs are clear.")
    lay = ("There is no fluid around the lungs or air leak. The unknown part looks normal today. No air leak. "
           "There is a 16 mm nodule in the left lung. The lungs are clear.")
    got = sentence_pairs(source, lay)
    assert got == [("There is no pleural effusion or pneumothorax.", "There is no fluid around the lungs or air leak.")]
    # XXXX sentence, a 3-word sentence, a changed number and side, and a copy are all left out


def test_sentence_pairs_drop_advice_added_by_the_plain_version():
    assert sentence_pairs("There is no pleural effusion or pneumothorax.",
                          "There is no fluid around the lungs or air leak, so there is nothing to worry about.") == []


def test_split_by_id_keeps_each_report_on_one_side_and_is_repeatable():
    pairs = [{"rid": str(i % 10), "source": f"s{i}", "target": f"t{i}"} for i in range(50)]
    train, val = split_by_id(pairs, 0.2, seed=1)
    assert len(train) + len(val) == 50 and val
    assert {p["rid"] for p in train}.isdisjoint({p["rid"] for p in val})
    assert split_by_id(pairs, 0.2, seed=1) == (train, val)
