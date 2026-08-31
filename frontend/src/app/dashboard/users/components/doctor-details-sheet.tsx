"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { RiEdit2Line, RiSettings3Line } from "@remixicon/react";
import { useState } from "react";
import { useConfigs } from "../../configuration/hooks/use-config";
import { UserResponse } from "../api/types";
import { DoctorAdjustLimitDialog } from "./doctor-adjust-limit-dialog";
import { DoctorManageKnowledgeDialog } from "./doctor-manage-knowledge-dialog";

export function DoctorDetailsSheet({
	isOpen,
	onOpenChange,
	doctor,
}: {
	isOpen: boolean;
	onOpenChange: (open: boolean) => void;
	doctor: UserResponse | null;
}) {
	const [isManageKnowledgeOpen, setIsManageKnowledgeOpen] = useState(false);
	const [isAdjustLimitOpen, setIsAdjustLimitOpen] = useState(false);

	const { data: configs } = useConfigs();
	const isGlobalLimitActive =
		configs?.find((c) => c.key === "GLOBAL_TOKEN_LIMIT_ACTIVE")?.value === "true";
	const spdveLimit = configs?.find((c) => c.key === "TOKEN_LIMIT_SPKK")?.value || "500000";
	const gpPlusLimit = configs?.find((c) => c.key === "TOKEN_LIMIT_GP")?.value || "250000";

	// Determine doctor type quota label if global mode is active
	const drTypeUpper = (doctor?.dr_type || "").toUpperCase();
	const isSpDVE =
		drTypeUpper.includes("SPKK") || drTypeUpper.includes("SPDVE") || drTypeUpper.includes("SPDV");
	const isGP = drTypeUpper.includes("GP") || drTypeUpper.includes("UMUM");
	const effectiveGlobalLimit = isSpDVE ? Number(spdveLimit) : isGP ? Number(gpPlusLimit) : 0;

	const hasCustomLimit =
		doctor?.token_limit !== null && doctor?.token_limit !== undefined && doctor.token_limit > 0;
	const effectiveLimit = hasCustomLimit
		? doctor.token_limit!
		: isGlobalLimitActive
			? effectiveGlobalLimit
			: (doctor?.token_limit ?? 0);
	const tokensUsed = doctor?.tokens_used ?? 0;
	const tokensRemaining = Math.max(0, effectiveLimit - tokensUsed);

	return (
		<Sheet open={isOpen} onOpenChange={onOpenChange}>
			<SheetContent className="sm:max-w-100 w-full p-0 flex flex-col h-full bg-white gap-0 border-l border-gray-200">
				<SheetHeader className="p-4 border-b border-gray-200 flex flex-row items-center">
					<SheetTitle className="text-base font-medium text-black-500 text-left">
						Doctor Information
					</SheetTitle>
				</SheetHeader>

				{doctor && (
					<>
						<div className="flex-1 overflow-y-auto pb-6">
							<Tabs defaultValue="information" className="w-full">
								<div className="px-6 pt-4">
									<TabsList
										variant="line"
										className="w-full justify-start h-auto p-0 bg-transparent gap-6"
									>
										<TabsTrigger
											value="information"
											className="font-medium text-sm text-zinc-600 hover:text-blue-700 data-active:text-blue-700 data-active:after:bg-blue-700 px-0 pb-2 cursor-pointer"
										>
											Doctor Information
										</TabsTrigger>
										<TabsTrigger
											value="settings"
											className="font-medium text-sm text-zinc-600 hover:text-blue-700 data-active:text-blue-700 data-active:after:bg-blue-700 px-0 pb-2 cursor-pointer"
										>
											Settings
										</TabsTrigger>
									</TabsList>
								</div>

								{/* 1. Doctor Information Tab */}
								<TabsContent value="information" className="p-6 m-0 flex flex-col gap-6">
									<div className="flex flex-col gap-1">
										<span className="text-sm text-black-300">Name</span>
										<span className="text-sm font-medium text-black-500">{doctor.name}</span>
									</div>

									<div className="flex flex-col gap-1">
										<span className="text-sm text-black-300">Role</span>
										<span className="text-sm font-medium text-black-500">Doctor</span>
									</div>

									<div className="flex flex-col gap-1">
										<span className="text-sm text-black-300">Email</span>
										<span className="text-sm font-medium text-black-500">
											{doctor.email || "-"}
										</span>
									</div>

									<div className="flex flex-col gap-1">
										<span className="text-sm text-black-300">Employee ID</span>
										<span className="text-sm font-medium text-black-500">
											{doctor.employee_id || "-"}
										</span>
									</div>

									<div className="flex flex-col gap-1">
										<span className="text-sm text-black-300">Dr Type</span>
										<div className="flex items-center gap-2">
											<span className="text-sm font-medium text-black-500">
												{doctor.dr_type || "-"}
											</span>
											{isGlobalLimitActive && !hasCustomLimit && (
												<span className="text-[11px] bg-blue-50 text-blue-600 px-2 py-0.5 rounded-full font-medium border border-blue-100">
													{isSpDVE
														? "SpDVE Global Quota"
														: isGP
															? "GP Plus Global Quota"
															: "Global Quota"}
												</span>
											)}
											{isGlobalLimitActive && hasCustomLimit && (
												<span className="text-[11px] bg-emerald-50 text-emerald-700 px-2 py-0.5 rounded-full font-medium border border-emerald-200">
													Custom Override
												</span>
											)}
										</div>
									</div>

									<div className="flex flex-col gap-1">
										<span className="text-sm text-black-300">Ecosystem</span>
										<span className="text-sm font-medium text-black-500">
											{doctor.ecosystem || "ERHA"}
										</span>
									</div>
								</TabsContent>

								{/* 2. Settings Tab */}
								<TabsContent value="settings" className="p-6 m-0 flex flex-col gap-6">
									{/* Token Management */}
									<div className="flex items-center justify-between gap-4">
										<div className="flex flex-col gap-1">
											<span className="text-sm text-black-300">Tokens Remaining</span>
											<div className="flex items-center gap-2 flex-wrap">
												<span className="text-sm font-medium text-blue-600">
													{tokensRemaining.toLocaleString()} / {effectiveLimit.toLocaleString()}{" "}
													<span className="text-black-500 font-normal">tokens</span>
												</span>
												{isGlobalLimitActive && !hasCustomLimit && (
													<span className="text-[11px] bg-blue-50 text-blue-600 px-2 py-0.5 rounded-full font-medium border border-blue-100">
														{isSpDVE
															? "SpDVE Global Quota"
															: isGP
																? "GP Plus Global Quota"
																: "Global Quota"}
													</span>
												)}
												{isGlobalLimitActive && hasCustomLimit && (
													<span className="text-[11px] bg-emerald-50 text-emerald-700 px-2 py-0.5 rounded-full font-medium border border-emerald-200">
														Custom Override
													</span>
												)}
											</div>
										</div>
										<Button
											type="button"
											variant="outline"
											className="border-gray-200 bg-white text-zinc-700 hover:bg-zinc-50 rounded-lg px-3 h-8 font-medium text-xs transition-colors cursor-pointer shadow-none gap-1.5 shrink-0"
											onClick={() => setIsAdjustLimitOpen(true)}
										>
											<RiEdit2Line className="size-3.5 shrink-0" />
											Adjust Limit
										</Button>
									</div>

									{/* Branch Setting */}
									<div className="flex flex-col gap-2">
										<span className="text-sm text-black-300">Branches</span>
										{doctor.branches && doctor.branches.length > 0 ? (
											<div className="flex flex-col gap-3">
												{doctor.branches.map((branch) => (
													<div
														key={branch.id}
														className="border border-black-50 rounded-md p-3 flex flex-col gap-1 bg-white"
													>
														<span className="text-sm font-medium text-black-500">
															{branch.name}
														</span>
														<span className="text-xs text-black-300">
															Branch Token Pool:{" "}
															{branch.token_limit
																? `${branch.token_limit.toLocaleString()} tokens/mo`
																: "Default"}
														</span>
													</div>
												))}
											</div>
										) : (
											<div className="border border-black-50 rounded-md p-3">
												<span className="text-sm text-black-300">No Branch</span>
											</div>
										)}
									</div>

									{/* Knowledge Base Setting */}
									<div className="flex flex-col gap-2">
										<span className="text-sm text-black-300">Knowledge Base</span>
										<div className="flex flex-wrap gap-2">
											{doctor.categories && doctor.categories.length > 0 ? (
												doctor.categories.map((cat) => (
													<Badge
														key={cat.id}
														variant="secondary"
														className="bg-black-50 text-black-500 font-normal text-xs"
													>
														{cat.name}
													</Badge>
												))
											) : (
												<span className="text-sm text-black-300">No categories assigned</span>
											)}
										</div>
										<Button
											type="button"
											variant="outline"
											className="w-full mt-2 border-gray-200 bg-white text-zinc-700 hover:bg-zinc-50 rounded-lg px-4 h-10 font-medium text-sm transition-colors cursor-pointer shadow-none gap-1.5"
											onClick={() => setIsManageKnowledgeOpen(true)}
										>
											<RiSettings3Line className="size-4 shrink-0" />
											Manage Knowledge Base
										</Button>
									</div>
								</TabsContent>
							</Tabs>
						</div>

						<DoctorManageKnowledgeDialog
							isOpen={isManageKnowledgeOpen}
							onOpenChange={setIsManageKnowledgeOpen}
							doctor={doctor}
						/>

						<DoctorAdjustLimitDialog
							isOpen={isAdjustLimitOpen}
							onOpenChange={setIsAdjustLimitOpen}
							doctor={doctor}
						/>
					</>
				)}
			</SheetContent>
		</Sheet>
	);
}
