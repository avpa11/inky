"""Build the bundled, authored B1 course. No network or generated-at-runtime lessons.

Each day pairs a thematic word and expression. Thirty grammar topics recur after
30 days with a new example, providing deliberate spaced review over 90 days.
"""
import json
from pathlib import Path

# theme | word (gender where relevant) | meaning | example | translation |
# expression | meaning | example | translation
ROWS = '''
Plans|un imprévu (m.)|an unexpected event|Un imprévu m'a obligé à annuler.|Something unexpected forced me to cancel.|au cas où|just in case|Prends un parapluie au cas où il pleuvrait.|Take an umbrella in case it rains.
Work|une échéance (f.)|a deadline; a due date|Nous devons respecter cette échéance.|We have to meet this deadline.|être débordé|to be overwhelmed with work|Je suis débordée cette semaine.|I'm swamped this week.
Housing|un bail (m.)|a lease|Le bail se termine en juin.|The lease ends in June.|se sentir chez soi|to feel at home|Je me sens enfin chez moi ici.|I finally feel at home here.
Decisions|un choix (m.)|a choice|Ce choix n'a pas été facile.|This choice wasn't easy.|peser le pour et le contre|to weigh the pros and cons|Prenons le temps de peser le pour et le contre.|Let's take time to weigh the pros and cons.
Travel|une correspondance (f.)|a connecting service|J'ai raté ma correspondance à Lyon.|I missed my connection in Lyon.|faire demi-tour|to turn back|La route est fermée, il faut faire demi-tour.|The road is closed; we have to turn back.
Friendship|un soutien (m.)|support; a source of support|Son soutien m'a beaucoup aidée.|Her support helped me a lot.|compter sur quelqu'un|to count on someone|Tu peux compter sur moi.|You can count on me.
Environment|le gaspillage (m.)|waste; wastefulness|Nous voulons réduire le gaspillage alimentaire.|We want to reduce food waste.|faire attention à|to pay attention to; be careful about|Je fais attention à ma consommation d'eau.|I watch how much water I use.
Shopping|un remboursement (m.)|a refund|J'ai demandé un remboursement.|I asked for a refund.|valoir le coup|to be worth it|Ce manteau est cher, mais il vaut le coup.|This coat is expensive, but it's worth it.
Learning|une compétence (f.)|a skill|Cette formation développe mes compétences.|This training develops my skills.|avoir du mal à|to have difficulty doing|J'ai du mal à comprendre cet accent.|I have trouble understanding this accent.
Time|un délai (m.)|a period allowed; a time limit|Le délai de livraison est de trois jours.|The delivery time is three days.|prendre son temps|to take one's time|Prends ton temps, nous ne sommes pas pressés.|Take your time; we're not in a hurry.
Cooking|une poignée (f.)|a handful; a handle|Ajoute une poignée de noix.|Add a handful of nuts.|mettre la main à la pâte|to lend a hand|Tout le monde a mis la main à la pâte.|Everyone lent a hand.
Health|un rendez-vous (m.)|an appointment|J'ai pris rendez-vous chez le dentiste.|I made a dentist's appointment.|se remettre de|to recover from|Elle se remet d'une mauvaise grippe.|She's recovering from a bad case of flu.
Money|une dépense (f.)|an expense|Il faut prévoir les dépenses du mois.|We need to plan this month's expenses.|mettre de côté|to put aside; save|Je mets un peu d'argent de côté.|I put a little money aside.
Opinions|un avis (m.)|an opinion; a notice|Ton avis m'intéresse.|I'm interested in your opinion.|à mon avis|in my opinion|À mon avis, nous devrions attendre.|In my opinion, we should wait.
Change|une habitude (f.)|a habit|J'essaie de changer mes habitudes.|I'm trying to change my habits.|petit à petit|little by little|Petit à petit, je prends confiance.|Little by little, I'm gaining confidence.
Transport|un trajet (m.)|a journey; a route|Le trajet dure quarante minutes.|The journey takes forty minutes.|être en panne|to have broken down|Le bus est en panne.|The bus has broken down.
Neighbors|le voisinage (m.)|the neighborhood; the neighbors|Le voisinage est très calme.|The neighborhood is very quiet.|donner un coup de main|to give someone a hand|Tu peux me donner un coup de main ?|Can you give me a hand?
Emotions|un soulagement (m.)|relief|Quel soulagement de te voir !|What a relief to see you!|en avoir assez|to have had enough|J'en ai assez de ce bruit.|I've had enough of this noise.
Communication|un malentendu (m.)|a misunderstanding|C'était simplement un malentendu.|It was simply a misunderstanding.|se rendre compte de|to realize; become aware of|Je me suis rendu compte de mon erreur.|I realized my mistake.
Culture|une œuvre (f.)|a work of art or literature|Cette œuvre me touche beaucoup.|This work moves me deeply.|avoir lieu|to take place|Le festival aura lieu en juillet.|The festival will take place in July.
Technology|un mot de passe (m.)|a password|J'ai oublié mon mot de passe.|I forgot my password.|mettre à jour|to update|Pense à mettre ton téléphone à jour.|Remember to update your phone.
Nature|un sentier (m.)|a footpath; a trail|Ce sentier mène au lac.|This trail leads to the lake.|prendre l'air|to get some fresh air|Allons prendre l'air après le repas.|Let's get some fresh air after lunch.
Workplace|un entretien (m.)|an interview; maintenance|Mon entretien s'est bien passé.|My interview went well.|être à l'aise|to feel comfortable; be at ease|Je suis plus à l'aise à l'oral.|I'm more comfortable speaking.
News|une source (f.)|a source|Il faut vérifier les sources.|We need to check the sources.|tenir au courant|to keep informed|Tiens-moi au courant de la situation.|Keep me informed about the situation.
Services|une démarche (f.)|an administrative step; an approach|Cette démarche peut se faire en ligne.|This procedure can be completed online.|s'y prendre à l'avance|to plan ahead|Il vaut mieux s'y prendre à l'avance.|It's better to plan ahead.
Goals|un objectif (m.)|a goal; an objective|Mon objectif est de parler plus souvent.|My goal is to speak more often.|tenir bon|to hold on; keep going|Tiens bon, tu progresses !|Keep going; you're making progress!
Invitations|un empêchement (m.)|something preventing attendance|J'ai un empêchement ce soir.|Something has come up tonight.|avec plaisir|with pleasure; gladly|Je viendrai avec plaisir.|I'd be happy to come.
Weather|une éclaircie (f.)|a sunny interval|Il y aura des éclaircies cet après-midi.|There will be sunny intervals this afternoon.|un temps de chien|awful weather|Il fait un temps de chien aujourd'hui.|The weather is awful today.
Organization|une tâche (f.)|a task|Cette tâche prend du temps.|This task takes time.|au fur et à mesure|as one goes along; gradually|Je range au fur et à mesure.|I tidy up as I go along.
Experience|un souvenir (m.)|a memory; a souvenir|Je garde un bon souvenir de ce voyage.|I have fond memories of that trip.|ça me rappelle|that reminds me of|Ça me rappelle mes vacances en Bretagne.|That reminds me of my holidays in Brittany.
Confidence|la confiance (f.)|trust; confidence|La confiance se construit avec le temps.|Trust is built over time.|oser se lancer|to dare to take the plunge|Il faut parfois oser se lancer.|Sometimes you have to dare to take the plunge.
Projects|un brouillon (m.)|a rough draft|J'ai terminé le premier brouillon.|I've finished the first draft.|être en cours|to be underway|Les travaux sont en cours.|The work is underway.
Renting|une caution (f.)|a guarantor; commonly, a rental deposit|L'agence demande une caution.|The agency asks for a guarantor or deposit.|faire l'état des lieux|to inspect a property's condition|Nous faisons l'état des lieux demain.|We're doing the property inspection tomorrow.
Arguments|un désaccord (m.)|a disagreement|Nous avons un désaccord sur le budget.|We disagree about the budget.|ne pas être du même avis|to disagree|Je ne suis pas du même avis.|I don't share that opinion.
Journeys|un détour (m.)|a detour|Les travaux nous obligent à faire un détour.|The roadworks force us to take a detour.|en avoir pour|to need a certain amount of time|On en a pour une heure.|It will take us an hour.
Relationships|un lien (m.)|a bond; a link|Nous avons gardé des liens très forts.|We've maintained very strong bonds.|prendre des nouvelles|to ask how someone is doing|J'appelle pour prendre de tes nouvelles.|I'm calling to see how you're doing.
Sustainability|le tri (m.)|sorting; waste sorting|Le tri des déchets est obligatoire ici.|Sorting waste is compulsory here.|faire le tri|to sort through things|Je fais le tri dans mes vêtements.|I'm sorting through my clothes.
Consumer life|une garantie (f.)|a warranty; a guarantee|Cet appareil est encore sous garantie.|This appliance is still under warranty.|faire une bonne affaire|to get a good deal|J'ai fait une bonne affaire au marché.|I got a good deal at the market.
Study|une lacune (f.)|a gap in knowledge|J'ai quelques lacunes en grammaire.|I have a few gaps in my grammar knowledge.|apprendre par cœur|to learn by heart|Je n'aime pas apprendre des listes par cœur.|I don't like learning lists by heart.
Patience|une attente (f.)|a wait; an expectation|L'attente a été plus longue que prévu.|The wait was longer than expected.|ça dépend|it depends|Ça dépend du temps qu'il fera.|It depends on what the weather will be like.
Food|un assaisonnement (m.)|seasoning; a dressing|Goûte pour vérifier l'assaisonnement.|Taste it to check the seasoning.|avoir l'eau à la bouche|to have one's mouth water|Cette odeur me met l'eau à la bouche.|That smell makes my mouth water.
Wellbeing|le repos (m.)|rest|Tu as besoin de repos.|You need some rest.|être en pleine forme|to feel great; be very fit|Après ces vacances, je suis en pleine forme.|After that holiday, I feel great.
Budget|une épargne (f.)|savings; saving|Cette épargne servira à financer le voyage.|These savings will help pay for the trip.|joindre les deux bouts|to make ends meet|Il est difficile de joindre les deux bouts.|It's hard to make ends meet.
Discussion|un point de vue (m.)|a point of view|Je comprends ton point de vue.|I understand your point of view.|cela dit|that said|C'est cher. Cela dit, la qualité est bonne.|It's expensive. That said, the quality is good.
Routine|un rythme (m.)|a rhythm; a pace|J'ai trouvé mon rythme.|I've found my rhythm.|de temps en temps|from time to time|Je travaille de chez moi de temps en temps.|I work from home from time to time.
Commuting|un abonnement (m.)|a subscription; a season ticket|Mon abonnement expire demain.|My season ticket expires tomorrow.|être à l'heure|to be on time|Pour une fois, le train est à l'heure.|For once, the train is on time.
Community|une entraide (f.)|mutual help|L'entraide est importante dans ce quartier.|Mutual support matters in this neighborhood.|rendre service|to do someone a favor|Merci, tu me rends vraiment service.|Thanks; you're really helping me out.
Feelings|une déception (f.)|a disappointment|Son départ a été une déception.|Her departure was a disappointment.|avoir le moral|to feel upbeat|Malgré la pluie, j'ai le moral.|Despite the rain, I'm in good spirits.
Understanding|une précision (f.)|a clarification; a detail|J'aurais besoin d'une précision.|I could use a clarification.|si j'ai bien compris|if I've understood correctly|Si j'ai bien compris, on part demain.|If I've understood correctly, we're leaving tomorrow.
Entertainment|une séance (f.)|a session; a screening|La prochaine séance commence à vingt heures.|The next screening starts at eight p.m.|ça vaut le détour|it's worth a special trip|Ce petit musée vaut le détour.|This small museum is worth a special trip.
Online life|une pièce jointe (f.)|an attachment|Le document est en pièce jointe.|The document is attached.|faire une sauvegarde|to make a backup|Fais une sauvegarde avant la mise à jour.|Make a backup before the update.
Outdoors|un paysage (m.)|a landscape; scenery|Le paysage change au fil des saisons.|The landscape changes with the seasons.|en plein air|outdoors; in the open air|Nous avons déjeuné en plein air.|We had lunch outdoors.
Career|une candidature (f.)|an application for a job or position|J'ai envoyé ma candidature hier.|I sent my application yesterday.|faire le point|to take stock; review the situation|Faisons le point sur tes projets.|Let's take stock of your plans.
Information|une rumeur (f.)|a rumor|Cette rumeur n'a pas été confirmée.|This rumor hasn't been confirmed.|à ce qu'il paraît|apparently; so it seems|À ce qu'il paraît, le magasin va fermer.|Apparently, the shop is going to close.
Paperwork|un justificatif (m.)|a supporting document; proof|Il faut un justificatif de domicile.|You need proof of address.|remplir un formulaire|to fill in a form|Vous devez remplir ce formulaire.|You must fill in this form.
Effort|un progrès (m.)|progress; an improvement|Tu as fait beaucoup de progrès.|You've made a lot of progress.|ça en vaut la peine|it's worth the effort|C'est difficile, mais ça en vaut la peine.|It's difficult, but it's worth the effort.
Social life|une occasion (f.)|an opportunity; an occasion|C'est une bonne occasion de discuter.|It's a good opportunity to talk.|à l'occasion|sometime; when the opportunity arises|On pourrait déjeuner ensemble à l'occasion.|We could have lunch together sometime.
Seasons|une averse (f.)|a shower of rain|Une averse nous a surpris.|We were caught in a shower.|être trempé jusqu'aux os|to be soaked to the skin|Sans parapluie, j'étais trempé jusqu'aux os.|Without an umbrella, I was soaked to the skin.
Priorities|une priorité (f.)|a priority|Le logement est notre priorité.|Housing is our priority.|chaque chose en son temps|one thing at a time|Chaque chose en son temps : finissons ceci.|One thing at a time: let's finish this.
Memories|une époque (f.)|a period; an era|À cette époque, je vivais à Lille.|At that time, I lived in Lille.|ça fait longtemps|it's been a long time|Ça fait longtemps qu'on ne s'est pas vus.|It's been a long time since we saw each other.
Initiative|une démarche (f.)|an approach; a course of action|J'apprécie ta démarche.|I appreciate your approach.|prendre les devants|to take the initiative|J'ai pris les devants et réservé une table.|I took the initiative and booked a table.
Teamwork|une répartition (f.)|a distribution; an allocation|La répartition des tâches est équitable.|The allocation of tasks is fair.|se mettre d'accord|to reach an agreement|Il faut se mettre d'accord sur une date.|We need to agree on a date.
Home repairs|une fuite (f.)|a leak|Il y a une fuite sous l'évier.|There's a leak under the sink.|faire appel à|to call on; seek help from|Nous avons fait appel à un plombier.|We called a plumber.
Choices|un compromis (m.)|a compromise|Nous avons trouvé un compromis.|We've found a compromise.|tant qu'à faire|while we're at it; if we're going to do it|Tant qu'à faire, restons tout le week-end.|While we're at it, let's stay all weekend.
Exploring|un repère (m.)|a landmark; a reference point|L'église nous sert de repère.|The church serves as our landmark.|se perdre|to get lost|On s'est perdus dans les petites rues.|We got lost in the little streets.
Kindness|une attention (f.)|a kind gesture; attention|C'est une délicate attention.|That's a thoughtful gesture.|ça me fait plaisir|that makes me happy|Ça me fait plaisir de te revoir.|I'm happy to see you again.
Resources|une ressource (f.)|a resource|Il faut préserver les ressources naturelles.|We need to preserve natural resources.|autant que possible|as much as possible|J'évite le plastique autant que possible.|I avoid plastic as much as possible.
Buying wisely|un rapport qualité-prix (m.)|value for money|Ce restaurant offre un bon rapport qualité-prix.|This restaurant offers good value for money.|à première vue|at first sight; at first glance|À première vue, tout semble en bon état.|At first glance, everything looks in good condition.
Practice|un acquis (m.)|something learned or gained|Il faut consolider ses acquis.|You need to consolidate what you've learned.|à force de|by repeatedly doing; through persistence|À force de pratiquer, je parle mieux.|Through practice, I speak better.
Availability|un créneau (m.)|a time slot|J'ai un créneau libre jeudi.|I have a free slot on Thursday.|d'ici là|by then; in the meantime|D'ici là, j'aurai fini le dossier.|By then, I'll have finished the file.
Eating out|une addition (f.)|a restaurant bill|L'addition est déjà réglée.|The bill has already been paid.|c'est ma tournée|it's my round|Ne paie pas, c'est ma tournée.|Don't pay; it's my round.
Balance|le bien-être (m.)|wellbeing|La marche contribue à mon bien-être.|Walking contributes to my wellbeing.|lever le pied|to slow down; ease off|Tu devrais lever le pied ce week-end.|You should take it easy this weekend.
Payments|un prélèvement (m.)|a direct debit; a deduction|Le prélèvement a lieu le cinq du mois.|The direct debit is taken on the fifth of the month.|être à découvert|to be overdrawn|Je fais attention à ne pas être à découvert.|I'm careful not to go overdrawn.
Debate|un argument (m.)|an argument; a supporting reason|Ton argument est convaincant.|Your argument is convincing.|en revanche|however; on the other hand|C'est petit. En revanche, c'est lumineux.|It's small. On the other hand, it's bright.
Adapting|un changement (m.)|a change|Ce changement me fait du bien.|This change is doing me good.|s'habituer à|to get used to|Je m'habitue à mon nouveau quartier.|I'm getting used to my new neighborhood.
Getting around|un quai (m.)|a platform; a quay|Le train part du quai numéro trois.|The train leaves from platform three.|être sur le point de|to be about to|Le train est sur le point de partir.|The train is about to leave.
Helping|le bénévolat (m.)|voluntary work|Je fais du bénévolat le samedi.|I volunteer on Saturdays.|de bon cœur|gladly; willingly|Je t'aide de bon cœur.|I'm happy to help you.
Resilience|une inquiétude (f.)|a worry; concern|Je comprends ton inquiétude.|I understand your concern.|ne pas baisser les bras|not to give up|Malgré les difficultés, elle ne baisse pas les bras.|Despite the difficulties, she doesn't give up.
Clarity|un renseignement (m.)|a piece of information|Je voudrais un renseignement, s'il vous plaît.|I'd like some information, please.|autrement dit|in other words|Autrement dit, il faut tout recommencer.|In other words, we have to start again.
Reading|un récit (m.)|a narrative; an account|Son récit m'a donné envie de voyager.|Her account made me want to travel.|avoir hâte de|to look forward to; be eager to|J'ai hâte de lire la suite.|I can't wait to read the rest.
Digital habits|un réglage (m.)|a setting; an adjustment|J'ai modifié les réglages de l'écran.|I changed the screen settings.|au lieu de|instead of|Appelle-moi au lieu d'envoyer un message.|Call me instead of sending a message.
Walking|une randonnée (f.)|a hike|Nous préparons une randonnée en montagne.|We're planning a mountain hike.|ça monte|it's uphill|Attention, ça monte après le pont !|Careful; it's uphill after the bridge!
Professional life|une responsabilité (f.)|a responsibility|Ce poste implique des responsabilités.|This position involves responsibilities.|être à la hauteur|to be up to the task|J'espère être à la hauteur.|I hope I'll be up to the task.
Perspective|un enjeu (m.)|a stake; an issue that matters|Les enjeux de cette décision sont importants.|A lot is at stake in this decision.|prendre du recul|to step back; gain perspective|J'ai besoin de prendre du recul.|I need to step back and gain perspective.
Public services|un guichet (m.)|a service counter; a ticket window|Le guichet ferme à midi.|The counter closes at noon.|faire la queue|to stand in line|Nous avons fait la queue pendant vingt minutes.|We stood in line for twenty minutes.
Achievement|une réussite (f.)|a success; an achievement|Cette soirée a été une réussite.|The evening was a success.|aller jusqu'au bout|to see something through|Je veux aller jusqu'au bout de ce projet.|I want to see this project through.
Hospitality|un accueil (m.)|a welcome; reception|Merci pour votre accueil chaleureux.|Thank you for your warm welcome.|faites comme chez vous|make yourself at home|Entrez et faites comme chez vous.|Come in and make yourself at home.
Climate|la sécheresse (f.)|drought; dryness|La sécheresse touche toute la région.|The drought is affecting the whole region.|faute de|for lack of|Faute de pluie, les plantes souffrent.|For lack of rain, the plants are suffering.
Simplifying|un rangement (m.)|tidying; storage|Cette pièce manque de rangements.|This room lacks storage space.|au quotidien|in everyday life; on a daily basis|Ce petit outil m'aide au quotidien.|This little tool helps me in everyday life.
Looking ahead|un souhait (m.)|a wish|Mon souhait est de continuer à apprendre.|My wish is to keep learning.|on verra bien|we'll see|Je vais essayer, et on verra bien.|I'll try, and we'll see.
'''

# topic | explanation | example 1 | translation 1 | example 2 | translation 2 | example 3 | translation 3 | usage note
GRAMMAR = '''
Depuis + present|Use the present for an action that began earlier and is still continuing.|J'habite ici depuis deux ans.|I've lived here for two years.|Elle apprend le français depuis janvier.|She's been learning French since January.|Nous attendons depuis une heure.|We've been waiting for an hour.|Depuis answers both 'since when?' and 'for how long?' for ongoing situations.
Passé composé or imparfait?|Imparfait sets the scene; passé composé presents a completed event.|Il pleuvait quand le bus est arrivé.|It was raining when the bus arrived.|Je cuisinais quand elle a appelé.|I was cooking when she called.|Nous marchions quand l'orage a commencé.|We were walking when the storm began.|Use the contrast to tell a story, rather than matching English tenses mechanically.
Si + imparfait|For a hypothetical present or future, use si + imparfait, then the conditional.|Si j'avais le temps, je viendrais.|If I had time, I would come.|Si nous habitions plus près, ce serait pratique.|If we lived closer, it would be convenient.|Si tu voulais, on pourrait partir tôt.|If you wanted, we could leave early.|Do not put the conditional directly after si in this pattern.
Polite conditional|The conditional softens a request or suggestion.|Je voudrais un renseignement.|I'd like some information.|Pourriez-vous répéter, s'il vous plaît ?|Could you repeat that, please?|Tu devrais te reposer.|You should rest.|Voudrais and pourrais are useful for requests; devrais often gives advice.
Qui or que?|Qui is the relative subject; que is the relative object.|C'est une amie qui habite à Lyon.|She's a friend who lives in Lyon.|Voici le livre que je cherche.|Here's the book I'm looking for.|Le train qui arrive est le nôtre.|The train that's arriving is ours.|Que becomes qu' before a vowel. Identify the subject of the relative verb first.
The pronoun y|Y often replaces à + a thing, or a place introduced by a preposition.|Tu vas au marché ? Oui, j'y vais.|Are you going to the market? Yes, I am.|Je pense à ce problème. J'y pense souvent.|I think about this problem. I think about it often.|Elle habite en France et elle y travaille.|She lives in France and works there.|With people, penser à usually keeps a stressed pronoun: je pense à elle.
The pronoun en|En replaces de + a thing, and can replace a noun after a quantity.|Tu veux du pain ? Oui, j'en veux.|Would you like bread? Yes, I'd like some.|J'ai trois billets. J'en ai trois.|I have three tickets. I have three of them.|Tu parles de ton voyage ? Oui, j'en parle.|Are you talking about your trip? Yes, I am.|Keep the quantity: j'en ai deux, j'en veux beaucoup.
Object pronoun position|Object pronouns normally go before the verb they belong to.|Je le vois demain.|I'm seeing him tomorrow.|Je vais lui téléphoner.|I'm going to phone her.|Tu peux m'aider ?|Can you help me?|With two verbs, place the pronoun before the infinitive when it belongs to that infinitive.
Direct or indirect object?|Many verbs take a direct object; téléphoner and parler take à + a person.|Je connais Marie. Je la connais.|I know Marie. I know her.|Je téléphone à Paul. Je lui téléphone.|I phone Paul. I phone him.|Je parle à mes voisins. Je leur parle.|I talk to my neighbors. I talk to them.|Lui can mean 'to him' or 'to her'; leur is the plural indirect object.
Comparisons|Use plus, moins, or aussi + adjective + que.|Ce trajet est plus court que l'autre.|This route is shorter than the other one.|Cette chambre est aussi claire que la mienne.|This room is as bright as mine.|Le train est moins cher que l'avion.|The train is cheaper than the plane.|Bon has the comparative meilleur; bien has mieux.
Better: mieux or meilleur?|Meilleur describes a noun; mieux usually describes how an action is done.|Ce pain est meilleur.|This bread is better.|Je comprends mieux maintenant.|I understand better now.|Cette solution me semble meilleure.|This solution seems better to me.|Meilleur agrees with the noun: meilleure, meilleurs, meilleures.
Future simple|Use the future simple for predictions, promises, and future events.|Je t'appellerai demain.|I'll call you tomorrow.|Nous verrons cela plus tard.|We'll look at that later.|Il fera beau dimanche.|The weather will be nice on Sunday.|Common irregular stems include ser-, aur-, ir-, fer-, and verr-.
Quand + future|For a future situation, French often uses the future in both clauses.|Quand tu arriveras, je préparerai le café.|When you arrive, I'll make coffee.|Dès que je saurai, je te dirai.|As soon as I know, I'll tell you.|Nous sortirons quand il fera moins chaud.|We'll go out when it's cooler.|English uses a present after 'when'; French normally uses a future here.
Venir de + infinitive|This construction expresses something that has just happened.|Je viens de rentrer.|I've just got home.|Elle vient de terminer son travail.|She's just finished her work.|Nous venons de recevoir la réponse.|We've just received the answer.|Conjugate venir, then add de and the infinitive.
Pendant or pour?|Pendant expresses duration; pour can express an intended duration.|J'ai attendu pendant une heure.|I waited for an hour.|Je pars pour trois jours.|I'm going away for three days.|Nous avons discuté pendant tout le trajet.|We talked throughout the journey.|For an action still continuing, use depuis rather than pendant.
Il faut + infinitive|Use il faut + infinitive to state a general necessity.|Il faut réserver à l'avance.|You need to book ahead.|Il faut prendre le temps de réfléchir.|You need to take time to think.|Il faut vérifier l'adresse.|You need to check the address.|Il faut que + a subject requires the subjunctive instead.
Subjunctive after il faut que|Use the subjunctive after il faut que to express necessity for a subject.|Il faut que tu viennes.|You need to come.|Il faut que nous partions tôt.|We need to leave early.|Il faut qu'elle soit là.|She needs to be there.|Common forms include sois, aies, ailles, fasses, and viennes.
Purpose with pour|Use pour + infinitive when the same person performs both actions.|Je marche pour rester en forme.|I walk to stay fit.|Elle économise pour voyager.|She's saving to travel.|Nous appelons pour confirmer.|We're calling to confirm.|Pour que + a different subject normally takes the subjunctive.
Because or thanks to?|Parce que introduces a clause; grâce à introduces a positive cause as a noun.|Je reste parce qu'il pleut.|I'm staying because it's raining.|Grâce à ton aide, j'ai terminé.|Thanks to your help, I've finished.|Le train est annulé à cause de la neige.|The train is canceled because of the snow.|À cause de often introduces an unwelcome cause; grâce à a helpful one.
Although with même si|Même si introduces a concession and normally takes the indicative.|Je sors même s'il pleut.|I'm going out even if it's raining.|Même si c'est cher, je vais l'acheter.|Even though it's expensive, I'm going to buy it.|Elle sourit même si elle est fatiguée.|She smiles even though she's tired.|Do not confuse this with bien que, which takes the subjunctive.
Negation: ne…plus|Ne…plus means 'no longer' or 'not anymore'.|Je ne travaille plus ici.|I don't work here anymore.|Nous n'avons plus de lait.|We have no milk left.|Elle ne prend plus le bus.|She no longer takes the bus.|In informal speech, ne is often omitted; keep it in careful writing.
Negation: ne…jamais|Ne…jamais means 'never'. In a compound tense, jamais usually follows the auxiliary.|Je ne mange jamais ici.|I never eat here.|Je n'ai jamais vu ce film.|I've never seen this film.|Elle n'est jamais allée à Nice.|She's never been to Nice.|Use déjà in a neutral 'ever' question: tu as déjà essayé ?
Restriction: ne…que|Ne…que means 'only', not a full negation.|Je n'ai que dix euros.|I only have ten euros.|Elle ne vient que le lundi.|She only comes on Mondays.|Nous ne restons que deux jours.|We're only staying two days.|Place que directly before the restricted element.
Reported statements|Use que to report what someone says or thinks.|Elle dit qu'elle est prête.|She says she's ready.|Je pense que c'est possible.|I think it's possible.|Il explique que le magasin est fermé.|He explains that the shop is closed.|Change pronouns as needed. Reporting with a past verb may require tense changes.
Indirect questions|An indirect question uses statement word order rather than inversion.|Je voudrais savoir où est la gare.|I'd like to know where the station is.|Tu sais quand il arrive ?|Do you know when he's arriving?|Je me demande si elle viendra.|I wonder whether she'll come.|Use si for an indirect yes/no question; omit est-ce que.
Relative où|Où can link a clause to a place or time.|C'est la ville où je suis né.|It's the city where I was born.|Je me souviens du jour où nous sommes partis.|I remember the day we left.|Voici le café où nous nous retrouvons.|Here's the café where we meet.|The accent distinguishes où ('where') from ou ('or').
Relative dont|Dont can replace de + a complement in a relative clause.|C'est le livre dont je t'ai parlé.|It's the book I told you about.|Voici le document dont j'ai besoin.|Here's the document I need.|C'est une réussite dont elle est fière.|It's an achievement she's proud of.|Think of the underlying forms: parler de, avoir besoin de, être fier de.
Agreement with être|With être, the past participle usually agrees with the subject.|Elle est arrivée hier.|She arrived yesterday.|Ils sont partis tôt.|They left early.|Nous sommes restées à la maison.|We stayed at home. (All-female group.)|Pronominal verbs need extra care; not every reflexive participle agrees automatically.
The gerund: en + -ant|The gerund often expresses simultaneous actions with the same subject.|J'écoute la radio en cuisinant.|I listen to the radio while cooking.|Elle apprend en pratiquant.|She learns by practicing.|Nous parlions en marchant.|We were talking while walking.|Useful irregular forms include en étant, en ayant, and en sachant.
Emphasis with c'est…qui|C'est…qui emphasizes the subject responsible for an action.|C'est moi qui ai réservé.|I'm the one who booked.|C'est toi qui choisis.|You're the one who chooses.|Ce sont eux qui organisent la fête.|They're the ones organizing the party.|The verb agrees with the emphasized subject: moi qui ai, toi qui as.
'''

def build():
    rows = [row.split('|') for row in ROWS.strip().splitlines()]
    grammar = [row.split('|') for row in GRAMMAR.strip().splitlines()]
    assert len(rows) == 90, len(rows)
    assert len(grammar) == 30, len(grammar)
    result = []
    for index, row in enumerate(rows):
        assert len(row) == 9, row
        theme, word, meaning, example, translation, phrase, phrase_meaning, phrase_example, phrase_translation = row
        g = grammar[index % 30]
        assert len(g) == 9, g
        review = index // 30
        vocab_note = "Neutral register. Learn the word with its example. Noun gender is shown as m. or f."
        if word.startswith('une caution'):
            vocab_note = "Neutral. Strictly a guarantor; often used for a rental deposit. Dépôt de garantie is precise for the deposit."
        phrase_note = "Everyday register. Practise this expression as a complete phrase."
        if index in (7, 27, 34, 46, 47, 57, 70, 71, 81, 89):
            phrase_note = "Conversational register. Natural with friends and colleagues; use care in formal writing."
        result.append({"id": index + 1, "theme": theme, "cards": [
            {"kind":"Vocabulary", "title":word, "meaning":meaning, "example":example, "translation":translation, "note":vocab_note},
            {"kind":"Expression", "title":phrase, "meaning":phrase_meaning, "example":phrase_example, "translation":phrase_translation, "note":phrase_note},
            {"kind":"Grammar", "title":g[0], "meaning":g[1], "example":g[2 + review*2], "translation":g[3 + review*2], "note":g[8]}
        ]})
    target = Path(__file__).resolve().parents[1] / 'inky_home/data/french.json'
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(f'Wrote {len(result)} daily sets / {sum(len(x["cards"]) for x in result)} cards')

if __name__ == '__main__':
    build()
