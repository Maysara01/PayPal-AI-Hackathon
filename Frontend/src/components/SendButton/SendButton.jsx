import "./SendButton.css";

function SendButton({ onClick, disabled }) {
  return (
    <button className="send-button" onClick={onClick} disabled={disabled}>
      Send
    </button>
  );
}

export default SendButton;
