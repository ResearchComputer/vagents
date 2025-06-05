// @ts-check
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';
import starlightThemeFlexoki from 'starlight-theme-flexoki'

export default defineConfig({
	integrations: [
		starlight({
			title: 'Vagents',
			customCss: [
				'./src/styles/custom.css',
			],
			plugins: [starlightThemeFlexoki()],
			social: [{ icon: 'github', label: 'GitHub', href: 'https://github.com/vagents-ai/vagents' }],
			sidebar: [
				{
					label: 'Guides',
					items: [
						{ label: 'Basic Programming', slug: 'guides/programming' },
						{ label: 'Compose a Module', slug: 'guides/compose-module' },
						{ label: 'Example: Deep Research', slug: 'guides/example-deep-research' },
					],
				},
				{
					label: 'Reference',
					autogenerate: { directory: 'reference' },
				},
			],
		}),
	],
});
