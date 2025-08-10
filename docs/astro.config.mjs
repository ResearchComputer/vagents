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
			defaultLocale: 'en',
			locales: {
				en: {
					label: 'English',
					lang: 'en',
				},
				'zh-cn': {
					label: '简体中文',
					lang: 'zh-CN',
				},
			},
            sidebar: [
                {
                    label: 'Getting Started',
                    translations: {
                        'zh-cn': '开始使用',
                        'en': 'Getting Started',
                    },
                    autogenerate: { directory: 'getting-started' },
                },
                {
                    label: 'Package Manager',
                    translations: {
                        'zh-cn': '包',
                        'en': 'Packages',
                    },
                    autogenerate: { directory: 'package-manager' },
                },
            ],
		}),
	],
});
