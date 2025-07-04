import React, { useState } from "react";

const Quiz = ({ questions }) => {
  const [currentQ, setCurrentQ] = useState(0);
  const [selected, setSelected] = useState(null);
  const [score, setScore] = useState(0);
  const [showScore, setShowScore] = useState(false);
  const [showResults, setShowResults] = useState(false);
  const [userAnswers, setUserAnswers] = useState({});

  const handleAnswer = (option) => {
    setSelected(option);
    const correct = option === questions[currentQ].correctAnswer;
    if (correct) setScore((prev) => prev + 1);
    setUserAnswers((prev) => ({ ...prev, [questions[currentQ].id]: option }));
  };

  const handleNext = () => {
    if (currentQ + 1 < questions.length) {
      setCurrentQ(currentQ + 1);
      setSelected(null);
    } else {
      setShowScore(true);
    }
  };

  const handleTryAgain = () => {
    setCurrentQ(0);
    setSelected(null);
    setScore(0);
    setShowScore(false);
    setShowResults(false);
    setUserAnswers({});
  };

  const isDarkMode =
    typeof window !== "undefined" &&
    window.matchMedia &&
    window.matchMedia("(prefers-color-scheme: dark)").matches;

  return (
    <section>
      <hr
        style={{
          borderTop: "3px solid var(--custom-blue)",
          opacity: 0.4,
          margin: "2rem auto",
          width: "95%",
        }}
      />
      <h3 className="mt-4 text-primary">Quick Quiz: Test Your Knowledge</h3>

      {!showScore && !showResults && (
        <>
          <p className="fs-5">
            {questions[currentQ].question}
          </p>
          <ul className="list-unstyled mx-auto" style={{ maxWidth: 400 }}>
            {questions[currentQ].options.map((option) => (
              <li key={option} className="mb-2">
                <button
                  className={`btn w-100 ${
                    selected === option ? "btn-primary" : "btn-outline-secondary "
                  }`}
                  onClick={() => handleAnswer(option)}
                  // disabled={selected !== null}
                >
                  {option}
                </button>
              </li>
            ))}
          </ul>
          {selected && (
            <button
              className="btn btn-primary text-white mt-3"
              onClick={handleNext}
            >
              {currentQ + 1 === questions.length ? "Finish" : "Next"}
            </button>
          )}
        </>
      )}


      {showScore && !showResults && (
        <div style={{ maxWidth: 800 }}>
          <p
            style={{
              fontSize: "1.3rem",
              fontWeight: "bold",
              marginTop: "1rem",
            }}
          >
            Your score: {score} / {questions.length}
          </p>
          <button
            onClick={() => setShowResults(true)}
            style={{
              marginRight: "1rem",
              padding: "8px 16px",
              cursor: "pointer",
              borderRadius: 4,
              backgroundColor: "var(--custom-blue)",
              color: "white",
              border: "none",
            }}
          >
            See Results
          </button>
          <button
            onClick={handleTryAgain}
            style={{
              padding: "8px 16px",
              cursor: "pointer",
              borderRadius: 4,
              backgroundColor: "#6c757d",
              color: "white",
              border: "none",
            }}
          >
            Try Again
          </button>
        </div>
      )}

      {showResults && (
        <div style={{ maxWidth: 800, marginTop: 20 }}>
          {questions.map((q) => {
            const userAnswer = userAnswers[q.id];
            const isCorrect = userAnswer === q.correctAnswer;
            const backgroundColor = isDarkMode
              ? "#444"
              : isCorrect
              ? "#d4edda"
              : "#f8d7da";

            const textColor = isDarkMode ? "#eee" : "#000";
            return (
              <div
                key={q.id}
                style={{
                  marginBottom: 20,
                  padding: 12,
                  border: isDarkMode ? "1px solid #555" : "1px solid #ddd",
                  borderRadius: 6,
                  backgroundColor,
                  color: textColor,
                }}
              >
                <p style={{ fontWeight: "bold" }}>{q.question}</p>
                <p>
                  Your answer:{" "}
                  <span style={{ fontWeight: "bold" }}>
                    {userAnswer || "No answer"}
                  </span>
                </p>
                {!isCorrect && (
                  <p>
                    Correct answer:{" "}
                    <span style={{ fontWeight: "bold" }}>
                      {q.correctAnswer}
                    </span>
                  </p>
                )}
              </div>
            );
          })}
          <button
            onClick={handleTryAgain}
            style={{
              padding: "8px 16px",
              cursor: "pointer",
              borderRadius: 4,
              backgroundColor: "var(--custom-blue)",
              color: "white",
              border: "none",
            }}
          >
            Try Again
          </button>
        </div>
      )}
    </section>
  );
};

export default Quiz;
