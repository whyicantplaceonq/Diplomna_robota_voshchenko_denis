using { /Fortnite.com/Devices }
using { /Verse.org/Simulation }
using { /UnrealEngine.com/Temporary/SpatialMath }
using { /UnrealEngine.com/Temporary/Diagnostics }

# Клас, що описує дані про покупку (розблоковуваний елемент)
purchase_data<public> := class<concrete>:
    @editable
    CreativeProps : []creative_prop = array{} # Список обєктів, які будуть переміщені при покупці

    @editable
    Price : int = 0 # Ціна покупки

    @editable
    ClaimerName : string = "" # Ім’я, яке буде показано на білборді

    @editable
    ClaimerLocation : vector3 = vector3{} # Позиція, куди буде телепортовано тригер

# Основний пристрій, який керує розблокуванням елементів
unlockables_device := class(creative_device):

    @editable
    GoldConditionalButton : conditional_button_device = conditional_button_device{} # Кнопка, яка перевіряє наявність золота

    @editable
    ClaimerTrigger : trigger_device = trigger_device{} # Тригер, який активує покупку

    @editable
    ClaimerBillboard : billboard_device = billboard_device{} # Білборд для відображення інформації про покупку

    @editable
    MoveOnZ : float = 1500.0 # Відстань переміщення обєктів по осі Z

    @editable
    PurchaseDatas : []purchase_data = array{} # Список всіх доступних покупок

        TextForUI<localizes>(InText : string): message = "{InText}" # Функція для локалізації тексту

        var MaybeOwnerAgent : ?agent = false # Агент, який володіє пристроєм
        var CurrentPurchaseIndex : int = 0 # Індекс поточної покупки
        var bBlockTriggerInteraction : logic = false # Блокування повторної взаємодії з тригером

        # Ініціалізація пристрою при старті
        OnBegin<override>()<suspends>:void=
            Print("OnBegin")

            # Підписка на події: вихід гравця та активація тригера
            GetPlayspace().PlayerRemovedEvent().Subscribe(OnPlayerLeft)
            ClaimerTrigger.TriggeredEvent.Subscribe(OnClaimerTriggered)

            # Переміщення всіх обєктів вниз (початковий стан)
            for (PurchaseData : PurchaseDatas):
                MoveProps(PurchaseData, false)

            # Переміщення тригера до першої покупки
            if (FirstPurchase := PurchaseDatas[0]):
                MoveClaimerToPurchase(FirstPurchase)

        # Обробка виходу гравця
        OnPlayerLeft(Agent : agent):void=
            if(OwnerAgent := MaybeOwnerAgent?, OwnerAgent = Agent):
                set MaybeOwnerAgent = false
                #  Повернення всіх куплених обєктів назад
                for (I := 0 .. CurrentPurchaseIndex-1, PurchaseData := PurchaseDatas[I]):
                    MoveProps(PurchaseData, false)

                # Скидання індексу покупки
                set CurrentPurchaseIndex = 0
                if(FirstPurchaseData := PurchaseDatas[0]):
                    MoveClaimerToPurchase(FirstPurchaseData)

        # Асинхронне розблокування взаємодії з тригером
        AsyncEnableTriggerInteraction()<suspends>:void=
            Sleep(1.0)
            set bBlockTriggerInteraction = false

        # Переміщення обєктів вгору або вниз
        MoveProps(PurchaseData : purchase_data, bMoveUp : logic):void=
            SignedMoveOnZ : float = if (bMoveUp = true)
                then MoveOnZ
                else -MoveOnZ

            for (CreativeProp : PurchaseData.CreativeProps):
                Transform := CreativeProp.GetTransform()
                var Location : vector3 = Transform.Translation
                set Location.Z += SignedMoveOnZ
                if (CreativeProp.TeleportTo[Location, Transform.Rotation]){}

        # Переміщення тригера до позиції покупки та оновлення білборда
        MoveClaimerToPurchase(PurchaseData : purchase_data):void=
            if (ClaimerTrigger.TeleportTo[PurchaseData.ClaimerLocation, IdentityRotation()]){}
        
            BillboardPriceString : string = if (PurchaseData.Price = 0)
                then "FREE"
                else "{PurchaseData.Price}"
        
            BillboardString : string = PurchaseData.ClaimerName + "\n" + BillboardPriceString
            ClaimerBillboard.SetText(TextForUI(BillboardString))
        
        # Обробка активації тригера
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

                    # Блокуємо повторну взаємодію на короткий час
                    set bBlockTriggerInteraction = true
                    spawn{ AsyncEnableTriggerInteraction() }

                    # Активуємо покупку: переміщення обєктів, списання золота
                    MoveProps(CurrentPurchaseData, true)
                    GoldConditionalButton.SetItemCountRequired(0, CurrentPurchaseData.Price)
                    GoldConditionalButton.Activate(Agent)

                    # Переходимо до наступної покупки
                    set CurrentPurchaseIndex +=1
                    if (CurrentPurchaseIndex = PurchaseDatas.Length):
                        var Location : vector3 = ClaimerTrigger.GetTransform().Translation
                        set Location.Z -= MoveOnZ
                        if (ClaimerTrigger.TeleportTo[Location, IdentityRotation()]){}
                    else if (NextPurchaseData := PurchaseDatas[CurrentPurchaseIndex]):
                        MoveClaimerToPurchase(NextPurchaseData)
