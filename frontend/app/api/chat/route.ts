import { TrueForge } from "@truefoundry/trueforge-sdk";

const client = new TrueForge({
  baseUrl: "https://c162-110-44-126-150.ngrok-free.app/",
  timeoutInSeconds: 600,
});

export async function POST(request: Request) {
  const { message, sessionId } = await request.json();

  if (!message || typeof message !== "string") {
    return Response.json({ error: "message is required" }, { status: 400 });
  }

  let sid = sessionId as string | undefined;

  if (!sid) {
    const { data: session } = await client.sessions.create({
      agent: {
        name: "trader_crypto",
      },
    });
    sid = session.id;
  }

  const stream = await client.sessions.createTurnStream(sid, {
    input: [{ type: "user.message", content: message }],
  });

  const encoder = new TextEncoder();
  const readable = new ReadableStream({
    async start(controller) {
      try {
        controller.enqueue(
          encoder.encode(
            JSON.stringify({ type: "session.id", sessionId: sid }) + "\n",
          ),
        );
        for await (const { data: event } of stream.withMetadata()) {
          controller.enqueue(encoder.encode(JSON.stringify(event) + "\n"));
          if (event.type === "turn.done") break;
        }
      } catch (err) {
        controller.enqueue(
          encoder.encode(
            JSON.stringify({ type: "error", message: String(err) }) + "\n",
          ),
        );
      } finally {
        controller.close();
      }
    },
  });

  return new Response(readable, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      Connection: "keep-alive",
    },
  });
}
