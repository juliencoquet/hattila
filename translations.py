"""
Translation module for URL analyzer insights
"""

class TranslationService:
    """Provides translations for insights between English and French"""
    
    def __init__(self):
        # Dictionary of metric names in French
        self.metric_names_fr = {
            'sessions': 'sessions',
            'active users': 'utilisateurs actifs',
            'page views': 'vues de page',
            'bounce rate': 'taux de rebond',
            'engagement rate': "taux d'engagement",
            'engaged sessions': 'sessions engagées',
            'key events': 'événements clés',
            'events': 'événements',
            'key events per session': 'événements clés par session',
            'user engagement duration': "durée d'engagement utilisateur",
            'average time on site': 'temps moyen sur le site',
            'conversion rate': 'taux de conversion',
            'purchases': 'achats',
            'transactions': 'transactions',
            'add-to-carts': 'ajouts au panier',
            'checkouts': 'passages en caisse',
            'e-commerce conversion rate': 'taux de conversion e-commerce',
            'cart abandonment rate': "taux d'abandon du panier",
            'pageviews per session': 'pages vues par session'
        }
        
        # Dictionary of channel names in French
        self.channel_names_fr = {
            'direct': 'direct',
            'organic': 'organique',
            'referral': 'référence',
            'email': 'email',
            'paid-search': 'recherche payante',
            'social': 'social',
            'affiliate': 'affilié',
            'display': 'display',
            'other': 'autre'
        }
        
        # Dictionary of device names in French
        self.device_names_fr = {
            'mobile': 'mobile',
            'desktop': 'ordinateur',
            'tablet': 'tablette'
        }
        
        # Common phrases for insight types in French
        self.phrases_fr = {
            'This URL received': 'Cette URL a reçu',
            'in the analyzed period': 'dans la période analysée',
            'This URL has a': 'Cette URL a un',
            'which is': 'qui est',
            'higher than': 'plus élevé que',
            'lower than': 'plus bas que',
            'the site average': 'la moyenne du site',
            'The top marketing channel for this URL is': 'Le principal canal marketing pour cette URL est',
            'bringing': 'apportant',
            'of traffic': 'du trafic',
            'This URL has limited channel diversity with only': 'Cette URL a une diversité de canaux limitée avec seulement',
            'channels, consider diversifying traffic sources': 'canaux, envisagez de diversifier les sources de trafic',
            'The': 'Le',
            'channel has the highest conversion rate at': 'canal a le taux de conversion le plus élevé à',
            'consider investing more in this channel': 'envisagez d\'investir davantage dans ce canal',
            'This URL triggered': 'Cette URL a déclenché',
            'events across': 'événements sur',
            'event types': "types d'événements",
            'The most common event on this URL is': "L'événement le plus courant sur cette URL est",
            'which occurred': 'qui s\'est produit',
            'times': 'fois',
            'has increased by': 'a augmenté de',
            'has decreased by': 'a diminué de',
            'for this URL over the period': 'pour cette URL sur la période',
            'The top device category for this URL is': "La principale catégorie d'appareil pour cette URL est",
            'accounting for': 'représentant',
            'of': 'de',
            'This URL has significant mobile traffic': 'Cette URL a un trafic mobile important',
            'ensuring mobile optimization is important': "assurer l'optimisation mobile est important",
            'Analysis for URL': "Analyse pour l'URL",
            'shows': 'montre',
            'data points across the specified time period': 'points de données sur la période spécifiée',
            'site-wide': 'à l\'échelle du site',
            # PageSpeed
            'Excellent mobile performance score of': 'Score de performance mobile excellent de',
            'Good mobile performance score of': 'Bon score de performance mobile de',
            'Average mobile performance score of': 'Score de performance mobile moyen de',
            'optimization recommended': 'optimisation recommandée',
            'Poor mobile performance score of': 'Mauvais score de performance mobile de',
            'significant optimization needed': 'optimisation significative nécessaire',
            'Mobile performance': 'Performance mobile',
            'is significantly worse than desktop': 'est significativement moins bonne que sur desktop',
            'Focus on mobile optimization': 'Concentrez-vous sur l\'optimisation mobile',
            'Desktop performance': 'Performance desktop',
            'is worse than mobile': 'est moins bonne que sur mobile',
            'Unusual pattern, check desktop optimization': 'Modèle inhabituel, vérifiez l\'optimisation desktop',
            'Slow First Contentful Paint of': 'Premier affichage de contenu lent de',
            'on mobile, aim for under 2s': 'sur mobile, visez moins de 2s',
            'Fast First Contentful Paint of': 'Premier affichage de contenu rapide de',
            'on mobile': 'sur mobile',
            'Poor Largest Contentful Paint of': 'Mauvais affichage du contenu principal de',
            'significantly affects perceived load speed': 'affecte significativement la vitesse de chargement perçue',
            'Excellent Largest Contentful Paint of': 'Excellent affichage du contenu principal de',
            'Poor Time to Interactive of': 'Mauvais temps avant interactivité de',
            'users may experience delays when interacting': 'les utilisateurs peuvent rencontrer des délais lors des interactions',
            'High Cumulative Layout Shift of': 'Décalage cumulatif de mise en page élevé de',
            'causing poor user experience with shifting content': 'causant une mauvaise expérience utilisateur avec un contenu qui se déplace',
            'Good visual stability with Cumulative Layout Shift of': 'Bonne stabilité visuelle avec un décalage cumulatif de mise en page de',


        }
    
    def translate_insight(self, insight, to_language='fr'):
        """
        Translate an insight to the target language.
        
        Args:
            insight (dict): The insight to translate
            to_language (str): Target language code ('fr' for French)
            
        Returns:
            dict: Translated insight
        """
        if to_language != 'fr':
            return insight  # Only support French for now
            
        # Create a new insight with the same properties
        translated = insight.copy()
        
        # Get the original finding text
        finding = insight['finding']
        
        # Translate based on insight type
        if insight['type'] == 'metric':
            # Handle metric insights
            if 'This URL received' in finding:
                metric = insight.get('metric', '')
                metric_name = self._get_metric_name(metric)
                metric_fr = self.metric_names_fr.get(metric_name, metric_name)
                
                # Extract the number
                parts = finding.split(' ')
                for i, part in enumerate(parts):
                    if part.isdigit() or (part.replace('.', '').isdigit() and '.' in part):
                        number = part
                        break
                
                translated['finding'] = f"Cette URL a reçu {number} {metric_fr} dans la période analysée"
                
        elif insight['type'] == 'conversion':
            # Handle conversion rate insights
            if 'conversion rate' in finding:
                # Extract values
                parts = finding.split('%')
                rate = parts[0].split('of ')[-1].strip()
                
                if 'which is' in finding:
                    # Compare to site average
                    comparison_parts = finding.split('which is')
                    comparison = comparison_parts[1].strip()
                    diff_pct = comparison.split('%')[0].strip()
                    comparison_type = 'plus élevé que' if 'higher' in comparison else 'plus bas que'
                    site_avg = comparison.split('than the site average (')[1].split('%')[0].strip()
                    
                    translated['finding'] = f"Cette URL a un taux de conversion de {rate}%, qui est {diff_pct}% {comparison_type} la moyenne du site ({site_avg}%)"
                else:
                    translated['finding'] = f"Cette URL a un taux de conversion de {rate}%"
                    
        elif insight['type'] == 'channel':
            # Handle channel insights
            if 'top marketing channel' in finding:
                # Extract channel name and values
                channel_start = finding.find("'") + 1
                channel_end = finding.find("'", channel_start)
                channel_name = finding[channel_start:channel_end]
                channel_fr = self.channel_names_fr.get(channel_name, channel_name)
                
                # Extract sessions and percentage
                remaining = finding[channel_end+1:]
                sessions = remaining.split('bringing ')[1].split(' sessions')[0]
                percentage = remaining.split('(')[1].split('%')[0]
                
                translated['finding'] = f"Le principal canal marketing pour cette URL est '{channel_fr}' apportant {sessions} sessions ({percentage}% du trafic)"
        
        elif insight['type'] == 'device':
            # Handle device insights
            if 'top device category' in finding:
                # Extract device name and values
                device_start = finding.find("'") + 1
                device_end = finding.find("'", device_start)
                device_name = finding[device_start:device_end]
                device_fr = self.device_names_fr.get(device_name, device_name)
                
                # Extract percentage
                percentage = finding.split('accounting for ')[1].split('%')[0]
                metric_name = finding.split('% of ')[1]
                metric_fr = self.metric_names_fr.get(metric_name, metric_name)
                
                translated['finding'] = f"La principale catégorie d'appareil pour cette URL est '{device_fr}' représentant {percentage}% de {metric_fr}"
        
        elif insight['type'] == 'trend':
            # Handle trend insights
            if 'increased by' in finding or 'decreased by' in finding:
                # Determine direction
                direction = 'augmenté' if 'increased' in finding else 'diminué'
                
                # Extract metric and percentage
                metric_name = finding.split(' has ')[0]
                metric_fr = self.metric_names_fr.get(metric_name, metric_name)
                
                percentage = finding.split('by ')[1].split('%')[0]
                
                translated['finding'] = f"{metric_fr} a {direction} de {percentage}% pour cette URL sur la période"
        
        elif insight['type'] == 'summary':
            # Handle summary insights
            if 'Analysis for URL' in finding:
                # Extract URL and data points
                url = finding.split('Analysis for URL ')[1].split(' shows')[0]
                data_points = finding.split('shows ')[1].split(' data')[0]
                
                translated['finding'] = f"Analyse pour l'URL {url} montre {data_points} points de données sur la période spécifiée"

        elif insight['type'] == 'pagespeed':
            # Handle PageSpeed insights
            if 'performance score' in finding:
                # Handle performance score insights
                if 'Excellent mobile performance score' in finding:
                    score = finding.split('of ')[1].split('/100')[0]
                    translated['finding'] = f"Score de performance mobile excellent de {score}/100"
                elif 'Good mobile performance score' in finding:
                    score = finding.split('of ')[1].split('/100')[0]
                    translated['finding'] = f"Bon score de performance mobile de {score}/100"
                elif 'Average mobile performance score' in finding:
                    score = finding.split('of ')[1].split('/100')[0]
                    translated['finding'] = f"Score de performance mobile moyen de {score}/100, optimisation recommandée"
                elif 'Poor mobile performance score' in finding:
                    score = finding.split('of ')[1].split('/100')[0]
                    translated['finding'] = f"Mauvais score de performance mobile de {score}/100, optimisation significative nécessaire"
            elif 'Mobile performance' in finding and 'significantly worse than desktop' in finding:
                # Handle mobile vs desktop comparison
                mobile_score = finding.split('Mobile performance (')[1].split(')')[0]
                desktop_score = finding.split('desktop (')[1].split(')')[0]
                translated['finding'] = f"Performance mobile ({mobile_score}) est significativement moins bonne que sur desktop ({desktop_score}). Concentrez-vous sur l'optimisation mobile."



        # If no specific translation was applied, try to use phrase replacements
        if translated['finding'] == finding:
            translated_text = finding
            
            # Replace phrases
            for en, fr in self.phrases_fr.items():
                translated_text = translated_text.replace(en, fr)
                
            # Replace metric names
            for en, fr in self.metric_names_fr.items():
                translated_text = translated_text.replace(en, fr)
                
            # Replace channel names
            for en, fr in self.channel_names_fr.items():
                translated_text = translated_text.replace(f"'{en}'", f"'{fr}'")
                
            translated['finding'] = translated_text
            
        return translated
    
    def _get_metric_name(self, metric_code):
        """Get the human-readable metric name from its code."""
        metric_map = {
            'sessions': 'sessions',
            'activeUsers': 'active users',
            'screenPageViews': 'page views',
            'engagementRate': 'engagement rate',
            'keyEvents': 'key events',
            'conversionRate': 'conversion rate'
        }
        return metric_map.get(metric_code, metric_code)


# Function to translate all insights in results
def translate_insights_in_results(results, target_language='fr'):
    """
    Translate all insights in analysis results.
    
    Args:
        results (dict): The analysis results
        target_language (str): Target language code
        
    Returns:
        dict: Results with translated insights
    """
    translator = TranslationService()
    translated_results = results.copy()
    
    # Translate insights for each URL
    for url, data in results.get('urls', {}).items():
        if 'insights' in data:
            translated_insights = []
            for insight in data['insights']:
                translated_insight = translator.translate_insight(insight, target_language)
                translated_insights.append(translated_insight)
            
            translated_results['urls'][url]['insights'] = translated_insights
    
    return translated_results

def translate_text(text, target_language):
    """
    Translate a text string to the target language.
    
    Args:
        text (str): Text to translate
        target_language (str): Target language code (e.g., 'fr', 'es')
        
    Returns:
        str: Translated text or original text if translation failed
    """
    # Print debug information
    print(f"Translating to language: {target_language}")
    
    # If the language is English, return the original text
    if target_language == 'en':
        return text
    
    # Force language to lowercase to handle potential case issues
    target_language = target_language.lower()
    
    # Simple dictionary for common terms (basic fallback)
    translations = {
        'fr': {
            'Analytics Report for': 'Rapport d\'analyse pour',
            'Report Date': 'Date du rapport',
            'Table of Contents': 'Table des matières',
            'Property Overview': 'Aperçu de la propriété',
            'Key Metrics': 'Métriques clés',
            'Analytics Report for {property_name} - {date}': 'Rapport d\'analyse pour {property_name} - {date}',
            'Analytics Report': 'Rapport d\'analyse',
            'Property': 'Propriété',
            'Report Date': 'Date du rapport',
            'Key Performance Metrics': 'Métriques de performance clés',
            'Key Insights': 'Insights clés',
            'URL Analysis': 'Analyse d\'URL',
            'PageSpeed Performance': 'Performance PageSpeed',
            'site average': 'moyenne du site',
            'This URL received' : 'Cette URL a reçu'
            # Add more French translations
        },
        'es': {
            'Analytics Report for': 'Informe de análisis para',
            'Report Date': 'Fecha del informe',
            'Table of Contents': 'Tabla de contenidos',
            # Spanish translations
        }
    }
    
    # Check if we have translations for this language
    if target_language in translations:
        language_dict = translations[target_language]
        print(f"Using {target_language} translations dictionary")
        
        # Check if we have a direct translation
        if text in language_dict:
            return language_dict[text]
        
        # Try to replace individual words/phrases
        translated_text = text
        for eng, trans in language_dict.items():
            translated_text = translated_text.replace(eng, trans)
        
        # If we made any replacements, return the result
        if translated_text != text:
            return translated_text
    else:
        print(f"No translation dictionary found for {target_language}")
    
    # If no translation was found, return the original text
    return text