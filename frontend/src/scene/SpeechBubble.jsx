// Pixel speech box. Long lines scroll inside the bubble (never cover the scene).
export default function SpeechBubble({ text }) {
  return (
    <div className="speech-bubble">
      <div className="speech-scroll">{text}</div>
      <div className="speech-tail" />
    </div>
  );
}
