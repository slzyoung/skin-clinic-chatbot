"use client";

import { Button } from "@/components/ui/button";
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from "@/components/ui/select";
import {
	RiArrowLeftSLine,
	RiArrowRightSLine,
	RiMoreLine,
} from "@remixicon/react";
import { useMemo } from "react";

export interface DataTablePaginationProps {
	page: number;
	pageSize: number;
	totalPages: number;
	totalItems: number;
	startIndex: number;
	endIndex: number;
	onPageChange: (page: number) => void;
	onPageSizeChange?: (size: number) => void;
	pageSizeOptions?: number[];
	itemName?: string;
	showPageSize?: boolean;
}

export function DataTablePagination({
	page,
	pageSize,
	totalPages,
	totalItems,
	startIndex,
	endIndex,
	onPageChange,
	onPageSizeChange,
	pageSizeOptions = [10, 20, 50, 100],
	itemName = "results",
	showPageSize = true,
}: DataTablePaginationProps) {
	// Build array of pages with ellipsis
	const paginationRange = useMemo(() => {
		const delta = 1;
		const range: (number | string)[] = [];

		if (totalPages <= 7) {
			for (let i = 1; i <= totalPages; i++) {
				range.push(i);
			}
			return range;
		}

		const left = Math.max(2, page - delta);
		const right = Math.min(totalPages - 1, page + delta);

		range.push(1);

		if (left > 2) {
			range.push("ellipsis-left");
		}

		for (let i = left; i <= right; i++) {
			range.push(i);
		}

		if (right < totalPages - 1) {
			range.push("ellipsis-right");
		}

		range.push(totalPages);

		return range;
	}, [page, totalPages]);

	if (totalItems === 0) {
		return null;
	}

	return (
		<div className="flex flex-col sm:flex-row items-center justify-between gap-4 py-3 px-1 text-sm text-zinc-600">
			{/* Left: Summary text */}
			<div className="text-xs text-zinc-500 order-2 sm:order-1">
				Showing <span className="font-medium text-zinc-900">{startIndex}</span> to{" "}
				<span className="font-medium text-zinc-900">{endIndex}</span> of{" "}
				<span className="font-medium text-zinc-900">{totalItems}</span> {itemName}
			</div>

			{/* Right: Controls (Page size + Page buttons) */}
			<div className="flex items-center gap-4 order-1 sm:order-2 flex-wrap justify-center sm:justify-end">
				{showPageSize && onPageSizeChange && (
					<div className="flex items-center gap-2 text-xs text-zinc-500">
						<span>Rows per page:</span>
						<Select
							value={String(pageSize)}
							onValueChange={(val) => {
								if (val) onPageSizeChange(Number(val));
							}}
						>
							<SelectTrigger className="h-8 w-18 px-2.5 text-xs bg-white border-gray-200 text-zinc-800 rounded-md">
								<SelectValue placeholder={String(pageSize)}>
									{String(pageSize)}
								</SelectValue>
							</SelectTrigger>
							<SelectContent align="end" alignItemWithTrigger={false} sideOffset={4} className="bg-white">
								{pageSizeOptions.map((size) => (
									<SelectItem key={size} value={String(size)} className="text-xs">
										{size}
									</SelectItem>
								))}
							</SelectContent>
						</Select>
					</div>
				)}

				<div className="flex items-center gap-1">
					{/* Previous button */}
					<Button
						type="button"
						variant="outline"
						size="sm"
						onClick={() => onPageChange(page - 1)}
						disabled={page <= 1}
						className="h-8 px-2.5 text-xs border-gray-200 bg-white text-zinc-700 hover:bg-zinc-50 disabled:opacity-40 disabled:cursor-not-allowed shadow-none gap-1"
					>
						<RiArrowLeftSLine className="size-4" />
						<span className="hidden xs:inline">Prev</span>
					</Button>

					{/* Numbered Page Buttons */}
					<div className="hidden sm:flex items-center gap-1">
						{paginationRange.map((item, index) => {
							if (typeof item === "string") {
								return (
									<span
										key={`ellipsis-${index}`}
										className="flex size-8 items-center justify-center text-zinc-400"
									>
										<RiMoreLine className="size-3.5" />
									</span>
								);
							}

							const isCurrent = item === page;

							return (
								<Button
									key={item}
									type="button"
									variant={isCurrent ? "default" : "ghost"}
									size="icon"
									onClick={() => onPageChange(item)}
									className={`size-8 text-xs font-medium rounded-md shadow-none ${
										isCurrent
											? "bg-zinc-900 text-white hover:bg-zinc-800"
											: "text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900"
									}`}
								>
									{item}
								</Button>
							);
						})}
					</div>

					{/* Mobile Page Indicator */}
					<span className="sm:hidden text-xs text-zinc-500 px-2 font-medium">
						{page} / {totalPages}
					</span>

					{/* Next button */}
					<Button
						type="button"
						variant="outline"
						size="sm"
						onClick={() => onPageChange(page + 1)}
						disabled={page >= totalPages}
						className="h-8 px-2.5 text-xs border-gray-200 bg-white text-zinc-700 hover:bg-zinc-50 disabled:opacity-40 disabled:cursor-not-allowed shadow-none gap-1"
					>
						<span className="hidden xs:inline">Next</span>
						<RiArrowRightSLine className="size-4" />
					</Button>
				</div>
			</div>
		</div>
	);
}
