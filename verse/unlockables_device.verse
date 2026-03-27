using { /Fortnite.com/Devices }
using { /Verse.org/Simulation }
using { /UnrealEngine.com/Temporary/SpatialMath }
using { /UnrealEngine.com/Temporary/Diagnostics }

##
# @class purchase_data
# @brief Дані про один розблоковуваний елемент тайкуну.
#
# Містить усі необхідні параметри для відображення та виконання
# однієї покупки: об'єкти що переміщуються, ціну, назву та позицію.
#
# @field CreativeProps  Список 3D-об'єктів які переміщуються вгору при покупці
# @field Price          Ціна покупки у внутрішній валюті (золото). 0 = безкоштовно
# @field ClaimerName    Назва елемента що відображається на білборді
# @field ClaimerLocation Позиція (vector3) куди телепортується тригер покупки
##
purchase_data<public> := class<concrete>:
    @editable
    CreativeProps : []creative_prop = array{}

    @editable
    Price : int = 0

    @editable
    ClaimerName : string = ""

    @editable
    ClaimerLocation : vector3 = vector3{}

##
# @class unlockables_device
# @brief Головний пристрій системи розблокування елементів тайкуну.
#
# Керує послідовним розблокуванням будівель/об'єктів за внутрішню валюту.
# Гравець підходить до тригера, натискає кнопку — об'єкт телепортується
# на свою позицію, золото списується. Після виходу гравця — скидання стану.
#
# @architecture
#   GoldConditionalButton → перевіряє баланс та списує золото
#   ClaimerTrigger        → точка взаємодії, телепортується до кожної покупки
#   ClaimerBillboard      → відображає назву та ціну поточної покупки
#   PurchaseDatas[]       → масив покупок у порядку їх розблокування
#
# @flow
#   OnBegin → MoveProps(all, down) → MoveClaimerToPurchase(first)
#   Player triggers → OnClaimerTriggered → check gold → MoveProps(up) → next purchase
#   Player leaves   → OnPlayerLeft → reset all props → reset index
##
unlockables_device := class(creative_device):

    @editable
    GoldConditionalButton : conditional_button_device = conditional_button_device{}

    @editable
    ClaimerTrigger : trigger_device = trigger_device{}

    @editable
    ClaimerBillboard : billboard_device = billboard_device{}

    @editable
    # Відстань переміщення об'єктів по осі Z при розблокуванні
    DefaultMoveDistance : float = 1500.0

    @editable
    PurchaseDatas : []purchase_data = array{}

        ##
        # @func TextForUI
        # @brief Обгортка для локалізації рядків у UI.
        # @param InText Вхідний рядок для відображення
        # @returns message Локалізоване повідомлення для білборда
        ##
        TextForUI<localizes>(InText : string): message = "{InText}"

        var MaybeOwnerAgent : ?agent = false
        var CurrentPurchaseIndex : int = 0
        var bBlockTriggerInteraction : logic = false

        ##
        # @func OnBegin
        # @brief Точка входу пристрою. Викликається при старті острова.
        #
        # Виконує початкову ініціалізацію:
        # 1. Підписується на PlayerRemovedEvent та TriggeredEvent
        # 2. Переміщує всі об'єкти вниз (початковий прихований стан)
        # 3. Телепортує тригер до першої покупки в масиві
        #
        # @suspends Асинхронна функція — виконується паралельно з ігровим циклом
        ##
        OnBegin<override>()<suspends>:void=
            Print("OnBegin")
            GetPlayspace().PlayerRemovedEvent().Subscribe(OnPlayerLeft)
            ClaimerTrigger.TriggeredEvent.Subscribe(OnClaimerTriggered)
            for (PurchaseData : PurchaseDatas):
                MoveProps(PurchaseData, false)
            if (FirstPurchase := PurchaseDatas[0]):
                MoveClaimerToPurchase(FirstPurchase)

        ##
        # @func OnPlayerLeft
        # @brief Обробник події виходу гравця з острова.
        #
        # Скидає стан системи якщо з острова вийшов саме власник
        # поточної сесії покупок (MaybeOwnerAgent). Повертає всі
        # вже куплені об'єкти у прихований стан та скидає індекс.
        #
        # @param Agent Гравець що покинув острів
        # @business-logic Лише власник може скинути стан. Якщо вийшов інший
        #                 гравець — нічого не відбувається.
        ##
        OnPlayerLeft(Agent : agent):void=
            if(OwnerAgent := MaybeOwnerAgent?, OwnerAgent = Agent):
                set MaybeOwnerAgent = false
                for (I := 0 .. CurrentPurchaseIndex-1, PurchaseData := PurchaseDatas[I]):
                    MoveProps(PurchaseData, false)
                set CurrentPurchaseIndex = 0
                if(FirstPurchaseData := PurchaseDatas[0]):
                    MoveClaimerToPurchase(FirstPurchaseData)

        ##
        # @func AsyncEnableTriggerInteraction
        # @brief Асинхронне зняття блокування тригера після затримки.
        #
        # Запускається через spawn після кожної покупки щоб запобігти
        # подвійним натисканням. Затримка 1.0 сек достатня для анімації
        # переміщення об'єктів.
        #
        # @suspends Асинхронна — виконується паралельно через spawn{}
        # @see bBlockTriggerInteraction
        ##
        AsyncEnableTriggerInteraction()<suspends>:void=
            Sleep(1.0)
            set bBlockTriggerInteraction = false

        ##
        # @func MoveProps
        # @brief Переміщує всі 3D-об'єкти покупки вгору або вниз по осі Z.
        #
        # Використовує TeleportTo для миттєвого переміщення кожного prop.
        # Напрямок визначається параметром bMoveUp:
        #   true  → +DefaultMoveDistance (об'єкт з'являється)
        #   false → -DefaultMoveDistance (об'єкт ховається під землю)
        #
        # @param PurchaseData Дані покупки з масивом CreativeProps
        # @param bMoveUp      true = вгору (розблокування), false = вниз (приховання)
        # @algorithm Для кожного prop: отримати Transform → змінити Z → TeleportTo
        ##
        MoveProps(PurchaseData : purchase_data, bMoveUp : logic):void=
            SignedMoveOnZ : float = if (bMoveUp = true)
                then DefaultMoveDistance
                else -DefaultMoveDistance
            for (CreativeProp : PurchaseData.CreativeProps):
                Transform := CreativeProp.GetTransform()
                var Location : vector3 = Transform.Translation
                set Location.Z += SignedMoveOnZ
                if (CreativeProp.TeleportTo[Location, Transform.Rotation]){}

        ##
        # @func MoveClaimerToPurchase
        # @brief Переміщує тригер та оновлює білборд для нової покупки.
        #
        # Викликається при ініціалізації та після кожної успішної покупки.
        # Телепортує ClaimerTrigger до ClaimerLocation поточної покупки
        # та оновлює текст на білборді (назва + ціна або "FREE").
        #
        # @param PurchaseData Дані наступної покупки
        # @ui Billboard format: "{ClaimerName}\n{Price}" або "{ClaimerName}\nFREE"
        ##
        MoveClaimerToPurchase(PurchaseData : purchase_data):void=
            if (ClaimerTrigger.TeleportTo[PurchaseData.ClaimerLocation, IdentityRotation()]){}
            BillboardPriceString : string = if (PurchaseData.Price = 0)
                then "FREE"
                else "{PurchaseData.Price}"
            BillboardString : string = PurchaseData.ClaimerName + "\n" + BillboardPriceString
            ClaimerBillboard.SetText(TextForUI(BillboardString))

        ##
        # @func OnClaimerTriggered
        # @brief Головний обробник натискання тригера гравцем.
        #
        # Містить основну бізнес-логіку системи розблокування:
        # 1. Ігнорує подію якщо bBlockTriggerInteraction = true
        # 2. Встановлює власника якщо це перша взаємодія
        # 3. Блокує взаємодію іншим гравцям (лише власник може купувати)
        # 4. Перевіряє баланс золота гравця
        # 5. Виконує покупку: переміщує об'єкти, списує золото
        # 6. Переходить до наступної покупки або ховає тригер якщо куплено все
        #
        # @param MaybeAgent Опціональний агент що активував тригер (?agent)
        # @business-logic Перший гравець що підійшов стає власником сесії.
        #                 Тільки він може продовжувати купувати.
        # @error-handling Недостатньо золота → Print + return (без списання)
        ##
        OnClaimerTriggered(MaybeAgent : ?agent):void=
            if (Agent := MaybeAgent?, bBlockTriggerInteraction = false):
                if (OwnerAgent := MaybeOwnerAgent?):
                    if(OwnerAgent <> Agent):
                        Print("Only the Owner Can Purchase!")
                        return
                else:
                    set MaybeOwnerAgent = option{ Agent }
                OwnerGold : int = GoldConditionalButton.GetItemCount(Agent, 0)
                if (CurrentPurchaseData := PurchaseDatas[CurrentPurchaseIndex]):
                    if (OwnerGold < CurrentPurchaseData.Price):
                        Print("Not Enough Money")
                        return
                    set bBlockTriggerInteraction = true
                    spawn{ AsyncEnableTriggerInteraction() }
                    MoveProps(CurrentPurchaseData, true)
                    GoldConditionalButton.SetItemCountRequired(0, CurrentPurchaseData.Price)
                    GoldConditionalButton.Activate(Agent)
                    set CurrentPurchaseIndex +=1
                    if (CurrentPurchaseIndex = PurchaseDatas.Length):
                        var Location : vector3 = ClaimerTrigger.GetTransform().Translation
                        set Location.Z -= DefaultMoveDistance
                        if (ClaimerTrigger.TeleportTo[Location, IdentityRotation()]){}
                    else if (NextPurchaseData := PurchaseDatas[CurrentPurchaseIndex]):
                        MoveClaimerToPurchase(NextPurchaseData)
