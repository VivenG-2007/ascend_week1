import type { TicketInfo } from "@/lib/api";

export default function TicketBanner({ ticket }: { ticket: TicketInfo }) {
  return (
    <div role="status" className="mt-3 rounded-md border border-amber-400 bg-amberwash px-3 py-2 text-sm text-amberink">
      A ticket was raised with {ticket.department}. Your ticket ID is <strong>{ticket.id}</strong>.
    </div>
  );
}
