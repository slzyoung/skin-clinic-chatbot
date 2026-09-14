import { Skeleton } from "@/components/ui/skeleton";

interface ChatHistorySummarySkeletonProps {
	count?: number;
}

export function ChatHistorySummarySkeleton({ count = 5 }: ChatHistorySummarySkeletonProps) {
	return (
		<div className="w-full">
			<div className="mb-4">
				<Skeleton className="h-6 w-36 rounded" />
				<Skeleton className="h-4 w-64 rounded mt-1" />
			</div>
			<div className="w-full overflow-x-auto pb-1">
				<div className="w-full min-w-190 flex items-center border border-gray-200 rounded-md bg-white overflow-hidden shadow-none">
					{Array.from({ length: count }).map((_, index) => (
						<div
							key={index}
							className={`flex-1 min-w-0 flex items-center gap-4 p-4 ${
								index !== count - 1 ? "border-r border-gray-200" : ""
							}`}
						>
							<Skeleton className="w-12 h-12 rounded-lg shrink-0" />
							<div className="min-w-0 flex-1 space-y-2">
								<Skeleton className="h-3.5 w-24 rounded" />
								<Skeleton className="h-6 w-12 rounded" />
							</div>
						</div>
					))}
				</div>
			</div>
		</div>
	);
}
