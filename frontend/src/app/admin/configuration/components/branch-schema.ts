import { z } from "zod";

export const branchSchema = z.object({
	name: z.string().min(1, "Name is required"),
	address: z.string().optional(),
	latitude: z
		.union([
			z.number(),
			z
				.string()
				.refine((val) => val === "" || !isNaN(parseFloat(val)), {
					message: "Latitude must be a valid number",
				})
				.transform((val) => (val === "" ? null : parseFloat(val))),
		])
		.nullable()
		.optional(),
	longitude: z
		.union([
			z.number(),
			z
				.string()
				.refine((val) => val === "" || !isNaN(parseFloat(val)), {
					message: "Longitude must be a valid number",
				})
				.transform((val) => (val === "" ? null : parseFloat(val))),
		])
		.nullable()
		.optional(),
	token_limit: z.union([
		z.number().min(0),
		z
			.string()
			.refine((val) => val === "" || !isNaN(parseInt(val, 10)), {
				message: "Token limit must be a valid number",
			})
			.transform((val) => (val === "" ? 0 : parseInt(val, 10))),
	]),
	image_url: z.string().nullable().optional(),
});

export type BranchValues = z.infer<typeof branchSchema>;

export const editTokenSchema = z.object({
	token_limit: branchSchema.shape.token_limit,
});

export type EditTokenValues = z.infer<typeof editTokenSchema>;
