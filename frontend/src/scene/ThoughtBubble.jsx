// A dashed "thinking" box shown under a character in god mode — the hidden
// scheme they'd never say out loud (dramatic irony). Long text scrolls inside.
export default function ThoughtBubble({ text }) {
  return (
    <div className="thought-bubble">
      <div className="thought-scroll">
        <span className="tb-dots">💭</span>
        {text}
      </div>
    </div>
  );
}
